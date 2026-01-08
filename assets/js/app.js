// --- Global Constants (from inline script in HTML) ---
// const MOKKAPI_ADMIN_PREFIX = ...;
// const CSRF_TOKEN = ...;
// const HOME_URL = ...;
// const USER = ...;
import { escapeHtml, getBadgeClass} from "./modules/utils";
import { ApiError } from "./modules/apiClient";
import { endpointsAPI, handlersAPI, authProfilesAPI } from './modules/resourceController';

document.addEventListener('DOMContentLoaded', () => {
    init();
});

// --- State ---
let currentEditingEndpoint = null; // Store endpoint details when editing
let currentEditingHandler = null;  // Store handler details when editing

// --- Selectors ---
let selectors = {}; // Object to hold selectors after init

function cacheSelectors() {
    selectors = {
        // Layout & Tree
        treeContainer: document.getElementById('tree-container'),
        resizer: document.getElementById("resizer"),
        sidebar: document.getElementById("sidebar"),
        mainContent: document.getElementById('main-content'),
        titleElement: document.getElementById('endpoint-title'),

        // Buttons
        createNewBtn: document.getElementById('create-new-btn'),

        // Tabs
        tabEndpointsLink: document.getElementById('tab-endpoints'),
        tabAuthLink: document.getElementById('tab-auth'),
        tabContentEndpoints: document.getElementById('tab-content-endpoints'),
        tabContentAuth: document.getElementById('tab-content-auth'),

        // Endpoint Details Area
        detailsContainer: document.getElementById('endpoint-details'),

        // Endpoint Form Area
        endpointFormContainer: document.getElementById('endpoint-form-container'),
        endpointForm: document.getElementById('endpoint-form'),
        endpointFormMode: document.getElementById('endpoint-form-mode'),
        endpointIdInput: document.getElementById('endpoint-id'),
        endpointPathInput: document.getElementById('endpoint-path-input'),
        endpointDescriptionInput: document.getElementById('endpoint-description-input'),
        initialHandlerSection: document.getElementById('initial-handler-section'),
        saveEndpointBtn: document.getElementById('save-endpoint-btn'),
        cancelEndpointBtn: document.getElementById('cancel-endpoint-edit-btn'),

        // Handler Form Area
        handlerFormContainer: document.getElementById('handler-form-container'),
        handlerForm: document.getElementById('handler-form'),
        handlerFormTitle: document.getElementById('handler-form-title'),
        handlerFormMode: document.getElementById('handler-form-mode'),
        handlerIdInput: document.getElementById('handler-id'),
        handlerEndpointIdInput: document.getElementById('handler-endpoint-id'),
        handlerMethodSelect: document.getElementById('handler-method-select'),
        handlerStatusInput: document.getElementById('handler-status-input'),
        handlerHeadersInput: document.getElementById('handler-headers-input'),
        handlerBodyInput: document.getElementById('handler-body-input'),
        handlerDescriptionInput: document.getElementById('handler-description-input'),
        saveHandlerBtn: document.getElementById('save-handler-btn'),
        cancelHandlerBtn: document.getElementById('cancel-handler-edit-btn'),

        // Auth Tab Area
        createAuthProfileBtn: document.getElementById('create-auth-profile-btn'),
        authProfileList: document.getElementById('auth-profile-list'),
        authProfileFormContainer: document.getElementById('auth-profile-form-container'),
        authFeedback: document.getElementById('auth-feedback-message'),
        handlerAuthSelect: document.getElementById('handler-auth-select'),


        // General Feedback
        feedbackDiv: document.getElementById('feedback-message'),
    };
}

// --- Initialization ---
async function init() {
    cacheSelectors();
    setupEventListeners();
    // populateAuthDropdown(); // TODO determine how to preload the auth section correctly
    await loadAndRenderEndpoints();
    showEndpointsTab(); // Start on endpoints tab
    loadAuthProfiles(); // Load initial auth profiles list
}

// --- Event Listeners Setup ---
function setupEventListeners() {
    // Resizer
    if (selectors.resizer && selectors.sidebar) {
        let x = 0;
        let sidebarWidth = selectors.sidebar.offsetWidth;

        const mouseMoveHandler = (e) => {
            const dx = e.clientX - x;
            sidebarWidth = selectors.sidebar.offsetWidth + dx;
            if (sidebarWidth < 150) sidebarWidth = 150;
            if (sidebarWidth > 600) sidebarWidth = 600; // Increased max width
            selectors.sidebar.style.width = sidebarWidth + "px";
            x = e.clientX;
        };

        const mouseUpHandler = () => {
            document.removeEventListener("mousemove", mouseMoveHandler);
            document.removeEventListener("mouseup", mouseUpHandler);
        };

        selectors.resizer.addEventListener("mousedown", (e) => {
            x = e.clientX;
            document.addEventListener("mousemove", mouseMoveHandler);
            document.addEventListener("mouseup", mouseUpHandler);
        });
    }

    // Tabs
    selectors.tabEndpointsLink?.addEventListener('click', (e) => { e.preventDefault(); showEndpointsTab(); });
    selectors.tabAuthLink?.addEventListener('click', (e) => { e.preventDefault(); showAuthTab(); });

    // Main Buttons
    selectors.createNewBtn?.addEventListener('click', () => displayEndpointForm('create'));

    // Endpoint Form Buttons
    selectors.endpointForm?.addEventListener('submit', handleEndpointFormSubmit);
    selectors.cancelEndpointBtn?.addEventListener('click', hideEndpointForm);

    // Handler Form Buttons
    selectors.handlerForm?.addEventListener('submit', handleHandlerFormSubmit);
    selectors.cancelHandlerBtn?.addEventListener('click', hideHandlerForm);

    // Auth Tab Buttons (Placeholders - require backend API/views)
    selectors.createAuthProfileBtn?.addEventListener('click', () => displayAuthProfileForm('create'));

    selectors.detailsContainer?.addEventListener('click', handleDetailsButtonClick);

    // Use delegation for auth list buttons if needed later
    selectors.authProfileList?.addEventListener('click', handleAuthListButtonClick);

}


function handleDetailsButtonClick(event) {
    const target = event.target;

    // Endpoint buttons
    if (target.id === 'edit-endpoint-btn') {
        const endpointId = target.dataset.endpointId;
        // Find endpoint data (assuming currentEditingEndpoint holds it)
        if (currentEditingEndpoint && currentEditingEndpoint.id == endpointId) {
             displayEndpointForm('edit', currentEditingEndpoint);
        } else { console.error("Couldn't find endpoint data for edit"); }
    } else if (target.id === 'delete-endpoint-btn-main') {
        const endpointId = selectors.endpointIdInput
        console.log(endpointId)
        if (endpointId) {
             endpointsAPI.delete(endpointId); // Call delete using ID
        } else { console.error("Couldn't find endpoint ID for delete"); }
    } else if (target.id === 'add-handler-btn') {
        const endpointId = target.dataset.endpointId;
        displayHandlerForm('create', null, endpointId);
    }
    // Handler buttons
    else if (target.classList.contains('edit-handler-btn')) {
        const handlerId = target.dataset.handlerId;
        displayHandlerForm('edit', handlerId);
    } else if (target.classList.contains('delete-handler-btn')) {
        const handlerId = target.dataset.handlerId;
        const method = target.dataset.method;
        const endpointPath = currentEditingEndpoint?.path; // Get path for confirm msg
        // TODO create intermediate function that handles the delete confirmation message
        deleteHandlerResource(handlerId);
    }
}

function handleAuthListButtonClick(event) {
    const target = event.target;
    if (target.classList.contains('edit-auth-btn')) {
        const profileId = target.dataset.profileId;
        alert(`Edit Auth Profile ${profileId} - Not implemented.`);
        // fetchAuthProfileAndShowForm(profileId);
    } else if (target.classList.contains('delete-auth-btn')) {
        const profileId = target.dataset.profileId;
         alert(`Delete Auth Profile ${profileId} - Not implemented.`);
        // deleteAuthProfile(profileId);
    }
}

async function deleteHandlerResource(handlerId) {
    if (!confirm('Delete this handler?')) return;
    await handlersAPI.delete(handlerId);

    const endpoint = await endpointsAPI.get(currentEditingEndpoint.id);
    if (endpoint.handlers.length) {
        await endpointsAPI.delete(currentEditingEndpoint.id);
        showFeedback('Handler deleted; endpoint had no more handlers and was removed.', false);
    } else {
        showFeedback('Handler deleted.', false);
    }
    setTimeout(() => window.location.reload(), 1500);
  }

async function loadAndRenderEndpoints() {
    showLoading(true); // Show loading indicator
    try {
        const endpointList = await endpointsAPI.list();
        if (endpointList){
            const structuredTreeData = buildTree(endpointList);
            renderTree(structuredTreeData);
        }
        else{
            selectors.treeContainer.innerHTML = '<p class="text-gray-500 text-sm">No endpoints defined yet.</p>';
        }
        showFeedback("Endpoints loaded.", false);
    } catch (error) {
        showFeedback(`Error loading endpoints: ${error.message}`, true);
        selectors.treeContainer.innerHTML = '<p class="text-red-500 text-sm">Could not load endpoints.</p>';
    } finally {
        showLoading(false);
    }
}

function showEndpointDetails(endpointDetails) {
    selectors.endpointId = endpointDetails.id
    // TODO show same forms in edit as create - ideally show ALL handler forms too
    // TODO tie authentication to method handler, not endpoint
    currentEditingEndpoint = endpointDetails; 
    currentEditingHandler = null;
    hideEndpointForm();
    hideHandlerForm();
    hideAuthManagement();

    let authProfileName = '<em class="text-gray-500">None</em>';
    if (endpointDetails.authentication_profile_id) {
        authProfileName = profile ? escapeHtml(profile.name) : '<em class="text-red-500">Unknown/Deleted Profile</em>';
    }

    let handlersHtml = '<p class="text-gray-500 text-sm">No handlers defined for this endpoint.</p>';
    if (endpointDetails.handlers && endpointDetails.handlers.length > 0) {
        // Sort handlers for consistent display (e.g., by method)
        const sortedHandlers = [...endpointDetails.handlers].sort((a, b) => {
            const methodOrder = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS', 'HEAD'];
            return methodOrder.indexOf(a.http_method) - methodOrder.indexOf(b.http_method);
        });

        handlersHtml = `
            <h5 class="text-base font-semibold mt-4 mb-2">Method Handlers:</h5>
            <ul class="space-y-2">
                ${sortedHandlers.map(handler => `
                    <li class="border rounded p-2 bg-gray-50 flex items-center justify-between">
                        <div>
                            <span class="font-mono font-bold ${getBadgeClass(handler.http_method)} px-2 py-0.5 rounded text-sm">${handler.http_method}</span>
                            <span class="ml-2 text-gray-700">(${handler.response_status_code})</span>
                            <span class="block text-xs text-gray-500 ml-1 mt-1">${escapeHtml(handler.description) || 'No description'}</span>
                        </div>
                        <div class="flex-shrink-0 ml-2">
                            <button class="edit-handler-btn text-blue-600 hover:text-blue-800 text-sm font-medium mr-2" data-handler-id="${handler.id}" title="Edit Handler">Edit</button>
                            <button class="delete-handler-btn text-red-600 hover:text-red-800 text-sm font-medium" data-handler-id="${handler.id}" data-method="${handler.http_method}" title="Delete Handler">Delete</button>
                        </div>
                    </li>
                `).join('')}
            </ul>
        `;
    }

    selectors.detailsContainer.innerHTML = `
        <div class="border rounded p-4 bg-white shadow-sm mb-4">
            <div class="mb-3 flex justify-between items-start">
                <div>
                    <h4 class="text-lg font-bold">/${escapeHtml(endpointDetails.path)}</h4>
                    <p class="text-sm text-gray-600">${escapeHtml(endpointDetails.description) || '<em>No description</em>'}</p>
                    <p class="text-sm mt-1"><strong>Authentication:</strong> ${authProfileName}</p>
                 </div>
                <div class="flex-shrink-0 space-x-1">
                    <button id="edit-endpoint-btn" data-endpoint-id="${endpointDetails.id}" class="bg-blue-500 hover:bg-blue-600 text-white text-xs py-1 px-2 rounded" title="Edit Endpoint Details (Path, Auth, Desc)">Edit Details</button>
                    <button id="delete-endpoint-btn-main" data-path="${endpointDetails.path}" class="bg-red-500 hover:bg-red-600 text-white text-xs py-1 px-2 rounded" title="Delete Entire Endpoint">Delete Endpoint</button>
                </div>
            </div>
            <hr class="my-3">
            ${handlersHtml}
            <button id="add-handler-btn" data-endpoint-id="${endpointDetails.id}" class="mt-4 bg-green-500 hover:bg-green-600 text-white text-sm py-1 px-3 rounded">Add New Handler</button>
        </div>
    `;
    selectors.titleElement.innerText = `Details for /${endpointDetails.path}`;
    selectors.detailsContainer.style.display = 'block';

    // Add event listeners for the new buttons dynamically
    attachDetailButtonListeners(endpointDetails);
}

// Attach listeners for buttons inside the details view
function attachDetailButtonListeners(endpointDetails) {
    const detailsNode = selectors.detailsContainer; // Scope listeners to the container
    detailsNode.querySelector('#edit-endpoint-btn')?.addEventListener('click', () => displayEndpointForm('edit', endpointDetails));
    detailsNode.querySelector('#delete-endpoint-btn-main')?.addEventListener('click', () => endpointsAPI.delete(endpointDetails.id)); // TODO add a 'are you sure' prompt and remove other listener
    detailsNode.querySelector('#add-handler-btn')?.addEventListener('click', () => displayHandlerForm('create', null, endpointDetails.id));

    detailsNode.querySelectorAll('.edit-handler-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const handlerId = e.target.dataset.handlerId;
            displayHandlerForm('edit', handlerId);
        });
    });
    detailsNode.querySelectorAll('.delete-handler-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const handlerId = e.target.dataset.handlerId;
            const method = e.target.dataset.method;
            deleteHandlerResource(handlerId);
        });
    });
}

function attachAuthButtonListeners() {
     selectors.authProfileList.querySelectorAll('.edit-auth-btn').forEach(btn => {
         btn.addEventListener('click', (e) => {
            const profileId = e.target.dataset.profileId;
            alert(`Edit Auth Profile ${profileId} - Form not implemented.`);
            // fetchAuthProfileAndShowForm(profileId);
         });
     });
      selectors.authProfileList.querySelectorAll('.delete-auth-btn').forEach(btn => {
         btn.addEventListener('click', (e) => {
            const profileId = e.target.dataset.profileId;
             alert(`Delete Auth Profile ${profileId} - API call not implemented.`);
            // deleteAuthProfile(profileId);
         });
     });
}

function renderTree(endpoints) {
    selectors.treeContainer.innerHTML = ''; 
    selectors.treeContainer.appendChild(createTree(endpoints));
}


function createTree(nodes) {
    const ul = document.createElement("ul");
    ul.className = "list-none pl-0 text-sm";

    nodes.forEach(node => {
        const li = document.createElement("li");
        li.className = "mb-1";

        const wrapper = document.createElement('div');
        wrapper.className = 'flex items-center p-1 rounded hover:bg-gray-200 transition-colors duration-150';

        const toggleSpan = document.createElement("span");
        toggleSpan.className = "mr-1 w-4 text-center"; 

        if (node.children && node.children.length > 0) {
            toggleSpan.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 inline transition-transform duration-150" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" /></svg>`;
            toggleSpan.style.cursor = 'pointer';
            toggleSpan.addEventListener("click", (e) => {
                e.stopPropagation();
                const childrenUl = li.querySelector('ul');
                const icon = toggleSpan.querySelector('svg');
                if (childrenUl) {
                    const isExpanded = childrenUl.style.display === "block";
                    childrenUl.style.display = isExpanded ? "none" : "block";
                    icon.style.transform = isExpanded ? 'rotate(0deg)' : 'rotate(90deg)';
                }
            });
        } else {
            toggleSpan.innerHTML = `<span class="text-gray-400">&bull;</span>`; 
        }
        wrapper.appendChild(toggleSpan);

        const labelSpan = document.createElement("span");
        labelSpan.textContent = node.name;
        labelSpan.className = "flex-1 truncate"; 

        if (node.is_endpoint) {
            labelSpan.classList.add("text-blue-600", "cursor-pointer", "font-medium"); 
            labelSpan.title = `Click to view /${node.path}`;
            labelSpan.addEventListener("click", (e) => {
                e.stopPropagation();
                showEndpointDetails(node.endpoint_details);
                hideEndpointForm();
                hideHandlerForm();
                hideAuthManagement();
            });

            const badgesSpan = document.createElement('span');
            badgesSpan.className = 'ml-2 flex-shrink-0';
            if (node.endpoint_details.authentication_profile_id) {
                badgesSpan.innerHTML += `<span class="bg-yellow-100 text-yellow-800 text-xs font-semibold mr-1 px-1.5 py-0.5 rounded border border-yellow-300" title="Auth Required">Auth</span>`;
            }
            if (node.endpoint_details.handlers) {
                node.endpoint_details.handlers.forEach(handler => {
                    const badgeColor = getBadgeClass(handler.http_method);
                    badgesSpan.innerHTML += `<span class="${badgeColor} text-xs font-semibold mr-1 px-1.5 py-0.5 rounded border" title="${handler.http_method}">${handler.http_method}</span>`;
                });
            }
             wrapper.appendChild(labelSpan); 
             wrapper.appendChild(badgesSpan);

        } else {
            labelSpan.classList.add("text-gray-600");
            labelSpan.title = `Intermediate path: ${node.path}`;
            wrapper.appendChild(labelSpan);
        }

        li.appendChild(wrapper);

        if (node.children && node.children.length > 0) {
            const childContainer = createTree(node.children);
            childContainer.style.display = "none";
            childContainer.className = "list-none pl-5";
            li.appendChild(childContainer);
        }
        ul.appendChild(li);
    });
    return ul;
}

/**
 * Build a nested tree from a flat list of endpoints.
 * Each node will have:
 *   - name: last segment of the path
 *   - path: full cumulative path (e.g. "/api/v1/users")
 *   - is_endpoint: true only on the leaf
 *   - endpoint_details: the original object (on the leaf)
 *   - children: []
 */
function buildTree(endpoints) {
    // Sort alphabetically by path so siblings end up ordered
    endpoints.sort((a, b) => a.path.localeCompare(b.path));
  
    const root = [];
  
    endpoints.forEach(ep => {
      // split out each segment, skipping empty string before first slash
      const parts = ep.path.split('/').filter(Boolean);
      let currentLevel = root;
      let cumulative = '';
  
      parts.forEach((segment, i) => {
        cumulative += '/' + segment;
        // see if we already created this node
        let node = currentLevel.find(n => n.name === segment);
  
        if (!node) {
          node = {
            name: segment,
            path: cumulative,
            is_endpoint: false,
            endpoint_details: null,
            children: []
          };
          currentLevel.push(node);
        }
  
        // if this is the last part, mark as an endpoint
        if (i === parts.length - 1) {
          node.is_endpoint = true;
          node.endpoint_details = ep;
        }
  
        // descend
        currentLevel = node.children;
      });
    });
  
    return root;
  }

// TODO refactor so all showFeedback calls include element explicitly.
function showFeedback(message, isError = false, feedbackElement) {
    if (feedbackElement) {
        feedbackElement.innerHTML = `<span class="${isError ? 'text-red-600' : 'text-green-600'}">${escapeHtml(message)}</span>`;
        return;
    }
    console.warn(message);
    return
    // Scroll into view smoothly if needed
    // feedbackElement.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// Simple loading indicator example
function showLoading(isLoading) {
    // Simple implementation: disable all buttons
    // Consider a more sophisticated overlay or spinner
    const buttons = document.querySelectorAll('button');
    buttons.forEach(btn => {
        // Avoid disabling buttons that shouldn't be disabled during loading if any
        btn.disabled = isLoading;
    });
    // Maybe show/hide a dedicated spinner element
    // const spinner = document.getElementById('loading-spinner');
    // if (spinner) spinner.style.display = isLoading ? 'block' : 'none';
    if (isLoading) console.log("Loading..."); // Placeholder
}

// Clear validation styles and messages from form fields
function clearFormErrors(formElement) {
    formElement?.querySelectorAll('.border-red-500').forEach(el => el.classList.remove('border-red-500'));
    formElement?.querySelectorAll('small.form-error-message').forEach(el => el.remove());
     // Clear general feedback too (optional, might want separate feedback)
    const feedbackDiv = document.getElementById('feedback-message'); // Find appropriate feedback div
    if (feedbackDiv) feedbackDiv.innerHTML = '';
}

// Display field-specific errors (assuming DRF-style error object)
function displayFormErrors(errors, formElement, feedbackElement) {
    let generalErrors = [];
    if (typeof errors === 'object' && errors !== null) {
        Object.entries(errors).forEach(([field, messages]) => {
            // Find input based on name attribute matching the field key
            const input = formElement?.elements[field];
            const message = Array.isArray(messages) ? messages.join(' ') : messages;

            if (input) {
                input.classList.add('border-red-500');
                // Display message near input
                let errorEl = input.parentElement?.querySelector(`small.form-error-message[data-field="${field}"]`);
                if (!errorEl) {
                    errorEl = document.createElement('small');
                    errorEl.className = 'text-red-500 text-xs mt-1 form-error-message block'; // Use block display
                    errorEl.dataset.field = field; // Mark field for clearing later
                    // Insert after the input or its helper text
                    input.parentElement?.appendChild(errorEl);
                }
                errorEl.textContent = message;
            } else {
                // Errors not specific to a field (e.g., 'non_field_errors', or other keys)
                generalErrors.push(`${field}: ${message}`);
            }
        });
    } else if (typeof errors === 'string') {
        // Handle simple string error messages
        generalErrors.push(errors);
    }

    // Display general errors in the main feedback div
    if (generalErrors.length > 0) {
         showFeedback(`Error: ${generalErrors.join('; ')}`, true, feedbackElement);
    }
}

function showEndpointsTab() {
    selectors.tabContentEndpoints.style.display = 'block';
    selectors.tabContentAuth.style.display = 'none';
    selectors.tabEndpointsLink.classList.add('border-indigo-500', 'text-indigo-600');
    selectors.tabEndpointsLink.classList.remove('border-transparent', 'text-gray-500', 'hover:text-gray-700', 'hover:border-gray-300');
    selectors.tabEndpointsLink.setAttribute('aria-current', 'page');
    selectors.tabAuthLink.classList.add('border-transparent', 'text-gray-500', 'hover:text-gray-700', 'hover:border-gray-300');
    selectors.tabAuthLink.classList.remove('border-indigo-500', 'text-indigo-600');
    selectors.tabAuthLink.removeAttribute('aria-current');
    hideEndpointForm(); // Hide forms when switching tabs
    hideHandlerForm();
}

function showAuthTab() {
    // TODO build out this functionality
    selectors.tabContentEndpoints.style.display = 'none';
    selectors.tabContentAuth.style.display = 'block';
    selectors.tabAuthLink.classList.add('border-indigo-500', 'text-indigo-600');
    selectors.tabAuthLink.classList.remove('border-transparent', 'text-gray-500', 'hover:text-gray-700', 'hover:border-gray-300');
    selectors.tabAuthLink.setAttribute('aria-current', 'page');
    selectors.tabEndpointsLink.classList.add('border-transparent', 'text-gray-500', 'hover:text-gray-700', 'hover:border-gray-300');
    selectors.tabEndpointsLink.classList.remove('border-indigo-500', 'text-indigo-600');
    selectors.tabEndpointsLink.removeAttribute('aria-current');
    loadAuthProfiles(); // Load/refresh auth profiles list
}


function hideEndpointForm() {
    selectors.endpointFormContainer.style.display = 'none';
    selectors.endpointForm.reset();
    currentEditingEndpoint = null;
    maybeShowPlaceholder();
}

function hideDetails() {
    selectors.detailsContainer.style.display = 'none';
    currentEditingEndpoint = null; // Clear selection when hiding details
}

function hideAuthManagement() { // Called when clicking endpoint in tree
    // Could switch back to endpoint tab or just hide auth form if shown
    if (selectors.tabContentAuth.style.display !== 'none') {
        showEndpointsTab();
    }
     // Also hide auth form if it's visible
    selectors.authProfileFormContainer.style.display = 'none';
}

function hideHandlerForm() {
    selectors.handlerFormContainer.style.display = 'none';
    selectors.handlerForm.reset();
    currentEditingHandler = null;
    maybeShowPlaceholder();
}

function maybeShowPlaceholder() {
    // If neither form nor details are showing, show the placeholder text
    if (selectors.endpointFormContainer.style.display === 'none' &&
        selectors.handlerFormContainer.style.display === 'none' &&
        selectors.detailsContainer.style.display === 'none')
    {
        selectors.titleElement.innerText = 'Select or Create Endpoint';
        selectors.detailsContainer.innerHTML = '<p class="text-gray-600">Click an endpoint from the tree to see its details, or click "Create New Endpoint".</p>';
        selectors.detailsContainer.style.display = 'block';
    }
}

async function displayHandlerForm(mode, handlerId = null, endpointId = null) {
    hideDetails();
    hideEndpointForm();
    hideAuthManagement();

    selectors.detailsContainer.style.display = 'none';

    selectors.handlerForm.reset();
    selectors.handlerFormMode.value = mode;
    selectors.handlerEndpointIdInput.value = endpointId;
    const profiles = await authProfilesAPI.list();
    selectors.handlerAuthSelect.innerHTML = profiles
        .map(p => `<option value="${p.id}">${p.name}</option>`)
        .join('');
    
    if (mode === 'edit') {
        const handlerData = await handlersAPI.get(handlerId);
        const endpointId = handlerData.endpoint
        const selected = handlerData.authentication_profile_ids || [];
        selectors.handlerAuthSelect.querySelectorAll('option').forEach(opt => {
            opt.selected = selected.includes(opt.value);
        });
        selectors.handlerFormTitle.innerText = `Edit ${handlerData.http_method} Handler for ${endpointId}`;
        selectors.handlerEndpointIdInput.value = endpointId;
        selectors.handlerIdInput.value = handlerId;
        selectors.handlerMethodSelect.value = handlerData.http_method;
        selectors.handlerMethodSelect.disabled = true; // Don't allow changing method on edit
        selectors.handlerStatusInput.value = handlerData.response_status_code || 200;
        // Handle headers - need to stringify the object for textarea
        try {
            selectors.handlerHeadersInput.value = JSON.stringify(handlerData.response_headers || {}, null, 2);
        } catch (e) { selectors.handlerHeadersInput.value = '{}'; } // Default if stringify fails
        selectors.handlerBodyInput.value = handlerData.response_body || '';
        selectors.handlerDescriptionInput.value = handlerData.description || '';
    } else { // mode === 'create'
        selectors.handlerFormTitle.innerText = `Create New Handler for ${currentEditingEndpoint?.path || selectors.handlerEndpointIdInput.value}`;
        selectors.handlerIdInput.value = '';
        selectors.handlerMethodSelect.disabled = false;
        // Status, headers, body already reset or have defaults set in HTML
    }
    selectors.feedbackDiv.innerHTML = ''; // Clear feedback
    selectors.handlerFormContainer.style.display = 'block';
     // Use generic title or update based on endpoint path?
    selectors.titleElement.innerText = selectors.handlerFormTitle.innerText;
    selectors.handlerMethodSelect.focus();
}

async function handleHandlerFormSubmit(event) {
    event.preventDefault();
    showFeedback('Saving handler...', false);

    const formData = new FormData(selectors.handlerForm);
    const mode = selectors.handlerFormMode.value;
    const handlerId = Number(selectors.handlerIdInput.value);
    const endpointId = Number(selectors.handlerEndpointIdInput.value);
    const selectedIds = [...selectors.handlerAuthSelect.selectedOptions]
        .map(opt => opt.value);
    // Validate headers JSON - later allow for invalid headers on purpose
    let headersJson;
    try {
        const headersRaw = formData.get('response_headers').trim();
        headersJson = headersRaw ? JSON.parse(headersRaw) : {};
        if (typeof headersJson !== 'object' || headersJson === null || Array.isArray(headersJson)) {
            throw new Error("Headers must be a JSON object (dictionary).");
        }
    } catch (e) {
         showFeedback(`Invalid JSON in Response Headers: ${e.message}`, true);
         return;
    }

    const payload = {
        // action: mode === 'create' ? 'create_handler' : 'update_handler',
        id: mode === 'edit' ? handlerId : null,
        endpoint: endpointId,
        http_method: selectors.handlerMethodSelect.value,
        response_status_code: parseInt(formData.get('response_status_code')) || 200,
        response_headers: headersJson,
        response_body: formData.get('response_body'),
        description: formData.get('description'),
        authentication_profile_ids: selectedIds,
    };
     try {
        if (mode === 'create'){
            const result = await handlersAPI.create(payload);
            showFeedback(result.message || 'Handler saved successfully.', false);
        }
        else if (mode === 'edit'){
            const result = await handlersAPI.update(handlerId, payload);
            showFeedback(result.message || 'Handler updated successfully.', false);
        }
        
        setTimeout(() => { window.location.reload(); }, 1500); // Reload to see changes
    } catch (error) {
        console.error('Handler Update/Create failed: ', error);
    }
}

function populateAuthDropdown(profiles) { // Accept profiles data
    selectors.endpointAuthSelect.innerHTML = '<option value="">-- No Authentication --</option>'; // Reset
    profiles.forEach(profile => {
        const option = document.createElement('option');
        option.value = profile.id;
        option.textContent = escapeHtml(profile.name);
        selectors.endpointAuthSelect.appendChild(option);
    });
}

function displayEndpointForm(mode, endpointData = null) {
    hideDetails();
    hideHandlerForm();
    hideAuthManagement();
    currentEditingEndpoint = mode === 'edit' ? endpointData : null;

    selectors.endpointForm.reset(); // Clear previous values
    selectors.endpointFormMode.value = mode;
    selectors.endpointPathInput.readOnly = (mode === 'edit');
    selectors.initialHandlerSection.style.display = (mode === 'create') ? 'block' : 'none';

    if (mode === 'edit' && endpointData) {
        selectors.endpointIdInput.value = endpointData.id;
        selectors.endpointPathInput.value = endpointData.path;
        selectors.endpointDescriptionInput.value = endpointData.description || '';
    } else { // mode === 'create'
        selectors.endpointIdInput.value = '';
        // Path, Desc, Auth already cleared by reset()
    }
    selectors.feedbackDiv.innerHTML = ''; // Clear feedback
    selectors.endpointFormContainer.style.display = 'block';
    selectors.endpointPathInput.focus();
}


// --- Form Submission Handlers ---
// TODO attach open endpoint to handler form
async function handleEndpointFormSubmit(event) {
    event.preventDefault();
    showFeedback('Saving Endpoint...', false);

    const formData = new FormData(selectors.endpointForm);
    const mode = selectors.endpointFormMode.value;

    const payload = {
        path: formData.get('path'),
        creator: USER,
        description: formData.get('description'),
        authentication_profile_id: null,
        handlers: []
    };

    if (mode === 'create') {
        const initialMethod = formData.get('initial_http_method');
        const initialBody = formData.get('initial_response_body');
        if (!initialMethod) {
            showFeedback("Initial handler method is required.", true);
            return;
        }
        payload.handlers.push({
             http_method: initialMethod,
             response_status_code: 200, // Default for initial
             response_headers: { "Content-Type": "application/json" }, // Default for initial
             response_body: initialBody,
             description: `${initialMethod} Handler (Initial)`
        });
        try {
            const created = await endpointsAPI.create(payload);
        } catch(err) {
            if (err instanceof ApiError){
                console.warn('API failed:', err.status, err.data);
                switch (err.status) {
                    case 400:
                    showValidationMessages(err.data);
                    break;
                    case 401:
                    redirectToLogin();
                    break;
                    default:
                    console.error(err.message);
                }
            } else if (err instanceof TypeError) {
            // network failure / CORS / DNS
            console.errro('Network error – check your connection');
            } else {
            // some other unexpected
            console.error(err);
            console.error('An unexpected error occurred');
            }
        }
        
    } else { // mode === edit
        const endpointId = selectors.endpointIdInput.value;
        try{
            const updated = await endpointsAPI.update(endpointId, payload); // TODO add try/catch block around all calls
        } catch(err) {
            if (err instanceof ApiError){
                console.warn('API failed:', err.status, err.data);
                switch (err.status) {
                    case 400:
                    showValidationMessages(err.data);
                    break;
                    case 401:
                    redirectToLogin();
                    break;
                    default:
                    console.error(err.message);
                }
            } else if (err instanceof TypeError) {
            // network failure / CORS / DNS
            console.error('Network error – check your connection');
            } else {
            // some other unexpected
            console.error(err);
            console.error('An unexpected error occurred');
            }
        }
    }
    setTimeout(() => { window.location.reload(); }, 1500); // TODO refactor out the timeout period here
}


// --- Placeholder Functions for Auth Management ---
async function loadAuthProfiles() {
    selectors.authProfileList.innerHTML = '<p class="text-gray-500">Loading...</p>';
    const auth_profiles = await authProfilesAPI.list()
    if (auth_profiles) {
         selectors.authProfileList.innerHTML = `
            <ul class="space-y-2">
                ${auth_profiles.map(p => `
                    <li class="border rounded p-2 flex justify-between items-center text-sm">
                        <span>${escapeHtml(p.name)}</span>
                        <div>
                            <button class="edit-auth-btn text-blue-600 hover:text-blue-800 mr-2" data-profile-id="${p.id}">Edit</button>
                            <button class="delete-auth-btn text-red-600 hover:text-red-800" data-profile-id="${p.id}">Delete</button>
                        </div>
                    </li>`).join('')}
            </ul>`;
        // Attach listeners for edit/delete auth buttons
        attachAuthButtonListeners();
    } else {
         selectors.authProfileList.innerHTML = '<p class="text-gray-500 text-sm">No authentication profiles defined yet.</p>';
    }
}

function displayAuthProfileForm(mode, profileData = null) {
    hideDetails();
    hideHandlerForm();
    hideEndpointForm()
    currentEditingAuthProfile = mode === 'edit' ? profileData : null;

}

async function handleAuthProfileFormSubmit(event){
    pass
}