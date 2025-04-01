# user_management/views.py
from django.contrib.auth.decorators import permission_required
from django.shortcuts import render, redirect
from .forms import UserCreationForm, PasswordResetForm

@permission_required('user_management.create_user')
def create_user(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('user_list')
    else:
        form = UserCreationForm()
    return render(request, 'user_management/create_user.html', {'form': form})

@permission_required('user_management.reset_user_password')
def reset_user_password(request, user_id):
    # TODO create this method
    pass