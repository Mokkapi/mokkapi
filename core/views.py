from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.http import JsonResponse, Http404, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

import json

from .forms import MokkEndpointForm
from .models import MokkBaseJSON
from .utils import build_folder_tree, build_tree


def process_and_save_endpoint(endpoint_data, user):
    path = endpoint_data.get('path')
    data_str = endpoint_data.get('data')

    if not path or data_str is None:
        raise ValueError("Each endpoint must have 'path' and 'data' keys.")

    # Validate the incoming JSON data string
    try:
        data = json.loads(data_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON data provided for path '{path or 'unknown'}': {e}")

    try:
        temp_instance = MokkBaseJSON(path=path, data=data, creator=user)
        existing = MokkBaseJSON.objects.filter(path=temp_instance.path).first()
        if existing:
            # update existing record
            existing.data = temp_instance.data
            existing.full_clean()
            existing.save()
            return existing, False
        else:
            temp_instance.save()
            return temp_instance, True
    except DjangoValidationError as e:
        # Re-raise with more context if possible, or just let it propagate
        raise DjangoValidationError(f"Validation failed for path '{path}': {e.message_dict}")
    except IntegrityError as e:
         if 'UNIQUE constraint' in str(e):
             # Path normalization happens in clean, so the constraint hits the normalized path
             normalized_path_guess = '/'.join(filter(None, path.strip().split('/'))) if path else path
             raise IntegrityError(f"An endpoint with a path resolving to '{normalized_path_guess}' already exists (or is duplicated in the bulk request).")
         else:
             raise IntegrityError(f"Database integrity error for path '{path}': {e}")
    # No need for a broad Exception catch here, let it propagate to the transaction handler


@login_required
def account_view(request):
    return render(request, 'mokkapi/account.html')


def get_json_content(request, url_path):
    try:
        mapping = MokkBaseJSON.objects.get(path=url_path)
    except MokkBaseJSON.DoesNotExist:
        raise Http404("No valid JSON exists at this endpoint")
    
    return JsonResponse(mapping.data)


@login_required
def home_view(request):
    if request.method == 'DELETE':
        try:
            payload = json.loads(request.body)
            # --- Check if it's a bulk delete (list) or a single delete (dict) ---
            if isinstance(payload, list):
                results = []
                errors = []
                try:
                    with transaction.atomic():
                        processed_paths = set()
                        for index, endpoint_data in enumerate(payload):
                            if not isinstance(endpoint_data, dict):
                                raise ValueError(f"Item at index {index} is not a valid JSON object.")
                            
                            raw_path = endpoint_data.get('path')
                            if not raw_path or not isinstance(raw_path, str):
                                raise ValueError(f"Item at index {index} is missing a valid 'path'.")
                            
                            normalized_path = '/'.join(filter(None, raw_path.strip().split('/')))
                            if not normalized_path:
                                raise ValueError(f"Item at index {index} has an empty or invalid path ('{raw_path}').")
                            if normalized_path in processed_paths:
                                raise ValueError(f"Duplicate path '{normalized_path}' found within the bulk request (item index {index}).")
                            
                            processed_paths.add(normalized_path)
                            
                            # Find and delete the endpoint
                            endpoint = MokkBaseJSON.objects.filter(path=normalized_path).first()
                            if endpoint:
                                endpoint.delete()
                                results.append({'path': normalized_path, 'status': 'deleted'})
                            else:
                                errors.append(f"No endpoint found with path '{normalized_path}' (item index {index}).")
                    
                    if errors:
                        return JsonResponse({
                            'error': 'Some endpoints were not found or could not be deleted.',
                            'details': errors
                        }, status=400)
                    else:
                        return JsonResponse({
                            'message': f'Bulk delete successful. {len(results)} endpoints deleted.',
                            'details': results
                        })
                except Exception as e:
                    return JsonResponse({
                        'error': f'Bulk delete failed: {str(e)}'
                    }, status=400)
            
            elif isinstance(payload, dict):
                raw_path = payload.get('path')
                if not raw_path or not isinstance(raw_path, str):
                    return JsonResponse({'error': "Missing valid 'path' in payload."}, status=400)
                normalized_path = '/'.join(filter(None, raw_path.strip().split('/')))
                endpoint = MokkBaseJSON.objects.filter(path=normalized_path).first()
                if endpoint:
                    endpoint.delete()
                    return JsonResponse({
                        'message': f'Endpoint {normalized_path} deleted successfully.',
                        'path': normalized_path
                    })
                else:
                    return JsonResponse({'error': f"No endpoint found with path '{normalized_path}'."}, status=400)
            
            else:
                return JsonResponse({'error': 'Invalid payload format. Expecting a JSON object or a list of objects.'}, status=400)
        
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON payload in request body.'}, status=400)
        except Exception as e:
            return JsonResponse({'error': f'An error occurred processing the delete request: {str(e)}'}, status=500)
    
    elif request.method == 'POST':
        try:
            payload = json.loads(request.body)

            # --- Check if it's a bulk upload (list) or single (dict) ---
            if isinstance(payload, list):
                # --- Bulk Processing ---
                results = []
                errors = []
                try:
                    with transaction.atomic(): # Ensures all or nothing
                        processed_paths = set() # Track paths within this bulk request for duplicates
                        for index, endpoint_data in enumerate(payload):
                            if not isinstance(endpoint_data, dict):
                                raise ValueError(f"Item at index {index} is not a valid JSON object.")

                             # Preliminary path check & normalization for duplicate check within payload
                            raw_path = endpoint_data.get('path')
                            if not raw_path or not isinstance(raw_path, str):
                                raise ValueError(f"Item at index {index} is missing a valid 'path'.")
                            normalized_path = '/'.join(filter(None, raw_path.strip().split('/')))
                            if not normalized_path:
                                raise ValueError(f"Item at index {index} has an empty or invalid path ('{raw_path}').")
                            if normalized_path in processed_paths:
                                raise ValueError(f"Duplicate path '{normalized_path}' found within the bulk request (item index {index}).")
                            processed_paths.add(normalized_path)


                            # Process and save using the helper
                            # Exceptions within process_and_save_endpoint will trigger rollback
                            endpoint, created = process_and_save_endpoint(endpoint_data, request.user)
                            action = "created" if created else "updated"
                            results.append({'path': endpoint.path, 'status': action})

                    # If transaction completes without error
                    return JsonResponse({
                        'message': f'Bulk operation successful. {len(results)} endpoints processed.',
                        'details': results
                    })

                except (ValueError, DjangoValidationError, IntegrityError, json.JSONDecodeError) as e:
                    # Transaction automatically rolled back
                    # Provide specific error if possible
                    error_detail = str(e)
                    # Try to extract dict for ValidationError
                    if isinstance(e, DjangoValidationError) and hasattr(e, 'message_dict'):
                        error_detail = e.message_dict

                    return JsonResponse({'error': 'Bulk operation failed. No changes were saved.', 'detail': error_detail}, status=400)
                except Exception as e:
                    # Catch other unexpected errors during bulk processing
                    # Log the error e
                    return JsonResponse({'error': f'An unexpected error occurred during bulk processing: {str(e)}'}, status=500)

            elif isinstance(payload, dict):
                # --- Single Endpoint Processing ---
                try:
                    # Use the same helper function for consistency
                    endpoint, created = process_and_save_endpoint(payload, request.user)
                    action = "created" if created else "updated"
                    return JsonResponse({
                        'message': f'Endpoint {endpoint.path} {action} successfully.',
                        'path': endpoint.path,
                        'data': endpoint.data
                    })
                except (ValueError, DjangoValidationError, IntegrityError, json.JSONDecodeError) as e:
                    error_detail = str(e)
                    if isinstance(e, DjangoValidationError) and hasattr(e, 'message_dict'):
                        error_detail = e.message_dict
                    return JsonResponse({'error': f"Failed to process endpoint: {error_detail}"}, status=400)
                except Exception as e:
                    # Log the error e
                    return JsonResponse({'error': f'An unexpected error occurred: {str(e)}'}, status=500)

            else:
                # Payload is neither list nor dict
                return JsonResponse({'error': 'Invalid payload format. Expecting a JSON object or a list of objects.'}, status=400)

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON payload in request body.'}, status=400)
        except Exception as e:
            # Log the error e
            return JsonResponse({'error': f'An error occurred processing the request: {str(e)}'}, status=500)

    # --- GET Request Logic (Remains the same) ---
    endpoints = MokkBaseJSON.objects.all().order_by('path')
    structured_endpoints = build_tree(list(endpoints))
    context = {
        'endpoints': endpoints,
        'structured_endpoints': structured_endpoints,
    }
    return render(request, 'mokkapi/home.html', context)

@require_GET # Only allow GET requests for serving JSON
def serve_json_view(request, endpoint_path):
    # Normalize the requested path *exactly* as it's stored in the DB
    normalized_path = endpoint_path.strip('/')
    try:
        # Find the endpoint by the normalized path
        endpoint = get_object_or_404(MokkBaseJSON, path=normalized_path)
        # Return the stored JSON data
        return JsonResponse(endpoint.data, safe=False) # safe=False allows non-dict JSON (like lists)
    except Http404:
        return JsonResponse({'error': 'Endpoint not found.'}, status=404)
    except Exception as e:
        # Log error e
        return JsonResponse({'error': 'Server error retrieving endpoint data.'}, status=500)


@login_required # Ensure only logged-in users can export
@require_GET    # Only allow GET requests
def export_endpoints_view(request):
    """
    Exports all endpoints as a JSON list, suitable for bulk import.
    """
    try:
        endpoints = MokkBaseJSON.objects.all().order_by('path')

        export_data = []
        for endpoint in endpoints:
            # Format data to match the expected bulk *input* format
            export_data.append({
                "path": endpoint.path,
                # Dump the JSON data field back into a string for the export file
                "data": json.dumps(endpoint.data, indent=2), # Pretty print JSON string
                # Optionally include 'name' if you use it
                # "name": endpoint.name
            })

        # Create filename with timestamp
        timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
        filename = f"mokkapi_endpoints_{timestamp}.json"

        # Create JSON response and set Content-Disposition for download
        response = JsonResponse(export_data, safe=False, json_dumps_params={'indent': 2}) # Pretty print the main list too
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    except Exception as e:
        # Log the error e
        # Return an error page or a simple error response
        # For simplicity, returning a basic HTTP error response:
        return HttpResponse(f"An error occurred during export: {str(e)}", status=500, content_type="text/plain")


"""
# Potentially superfluous:
@login_required
def json_form_view(request):
    # View for handling the JSON data form.
    
    # If we're editing an existing instance, retrieve it by path
    path_param = request.GET.get('path')
    instance = None
    if path_param:
        try:
            instance = MokkBaseJSON.objects.get(path=path_param)
        except MokkBaseJSON.DoesNotExist:
            messages.error(request, f"The requested endpoint '{path_param}' doesn't exist.")
            return redirect('home')
    
    if request.method == 'POST':
        # Pass the instance if we're editing an existing record
        form = MokkEndpointForm(request.POST, instance=instance)
        if form.is_valid():
            # Save the model instance
            mokk_endpoint = form.save()
            
            # Add a success message
            if instance:
                messages.success(request, f'Endpoint "{mokk_endpoint.path}" updated successfully!')
            else:
                messages.success(request, f'New endpoint "{mokk_endpoint.path}" created successfully!')
            
            # Redirect to the endpoint list
            return redirect('home')
    else:
        # Initialize with existing instance or empty form
        form = MokkEndpointForm(instance=instance)
    
    return render(request, 'mokkapi/new_endpoint.html', {
        'form': form,
        'title': 'Manage JSON Endpoint',
        'description': 'Create or edit an API endpoint and its associated JSON data',
        'is_edit': instance is not None,
    })

@login_required
def endpoint_list_view(request):
    # View for displaying all endpoints.
    endpoints = MokkBaseJSON.objects.all().order_by('path')
    return render(request, 'mokkapi/endpoints.html', {
        'endpoints': endpoints,
        'title': 'JSON Endpoints',
        'description': 'View and manage all JSON endpoints',
    })

@login_required
def delete_endpoint_view(request, path):
    # View for deleting an endpoint using path as the identifier.
    if request.method == 'POST':
        # URL decode the path if necessary (important for paths with slashes)
        from urllib.parse import unquote
        decoded_path = unquote(path)
        
        try:
            endpoint = MokkBaseJSON.objects.get(path=decoded_path)
            endpoint_path = endpoint.path  # Save for the message
            endpoint.delete()
            messages.success(request, f'Endpoint "{endpoint_path}" was deleted successfully.')
        except MokkBaseJSON.DoesNotExist:
            messages.error(request, f"The endpoint '{decoded_path}' you tried to delete doesn't exist.")
    
    return redirect('home')

@login_required
def create_endpoint(request):
    if request.method == "POST":
        form = MokkEndpointForm(request.POST)
        if form.is_valid():
            mokkEndpoint = form.save(commit=False)
            mokkEndpoint.created_by = request.user
            mokkEndpoint.save()
            return redirect('home')
    else:
        form = MokkEndpointForm()
    
    context = {'form': form}
    return render(request, 'mokkapi/create_endpoint.html', context)

@login_required
def edit_endpoint(request, pk):
    endpoint = get_object_or_404(MokkBaseJSON, pk=pk, created_by=request.user)
    
    if request.method == "POST":
        form = MokkEndpointForm(request.POST, instance=endpoint)
        if form.is_valid():
            form.save()
            return redirect('home')  # Redirect back to the home page after saving.
    else:
        form = MokkEndpointForm(instance=endpoint)
    
    context = {'form': form, 'endpoint': endpoint}
    return render(request, 'mokkapi/edit_endpoint.html', context)"

"""