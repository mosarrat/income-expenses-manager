from django.shortcuts import render,  redirect
from django.views import View
import json
from django.http import JsonResponse
from django.contrib.auth.models import User
import json
from django.http import JsonResponse
from django.contrib.auth.models import User
from validate_email import validate_email
from django.contrib import messages
from django.core.mail import EmailMessage

from django.utils.encoding import force_bytes, force_str, DjangoUnicodeDecodeError
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.contrib.sites.shortcuts import get_current_site
from django.urls import reverse
from .utils import account_activation_token
from django.core.mail import send_mail
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.contrib import auth
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator


# Create your views here.

#Email validation
class EmailValidationView(View):
    def post(self, request):
        data = json.loads(request.body)
        email = data['email']
        if not validate_email(email):
            return JsonResponse({'email_error': 'Email is invalid'}, status=400)
        if User.objects.filter(email=email).exists():
            return JsonResponse({'email_error': 'Sorry email in use,choose another one '}, status=409)
        return JsonResponse({'email_valid': True})

#User Name Validation
class UsernameValidationView(View):
    def post(self, request):
        data = json.loads(request.body)
        username = data['username']
        if not str(username).isalnum():
            return JsonResponse({'username_error': 'Username should only contain alphanumeric characters'}, status=400)
        if User.objects.filter(username=username).exists():
            return JsonResponse({'username_error': 'Sorry username in use,choose another one '}, status=409)
        return JsonResponse({'username_valid': True})

class RegistrationView(View):
    def get(self, request):
        return render(request, 'authentication/register.html')

    def post(self, request):
        #Get the user Data
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        # validata user data
        context = {
            'fieldValues': request.POST
        }
        # create a user account
      
        if not User.objects.filter(username=username).exists():
            if not User.objects.filter(email=email).exists():
                if len(password) < 6:
                    messages.error(request, 'Password too short')
                    return render(request, 'authentication/register.html', context)

                user = User.objects.create_user(username=username, email=email)
                user.set_password(password)
                user.is_active = False
                user.save()
                current_site = get_current_site(request)
                email_body = {
                    'user': user,
                    'domain': current_site.domain,
                    'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                    'token': account_activation_token.make_token(user),
                }

                link = reverse('activate', kwargs={
                               'uidb64': email_body['uid'], 'token': email_body['token']})

                email_subject = 'Activate your account'

                activate_url = 'http://'+current_site.domain+link

                email = EmailMessage(
                    email_subject,
                    'Hi '+user.username + ', Please the link below to activate your account \n'+activate_url,
                    'noreply@semycolon.com',
                    [email],
                )
                email.send(fail_silently=False)
                messages.success(request, 'Account successfully created')
                return render(request, 'authentication/register.html')

        return render(request, 'authentication/register.html')



class VerificationView(View):
    def get(self, request, uidb64, token):
        try:
            id = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=id)

            if not account_activation_token.check_token(user, token):
                return redirect('login'+'?message='+'User already activated')

            if user.is_active:
                return redirect('login')
            user.is_active = True
            user.save()

            messages.success(request, 'Account activated successfully')
            return redirect('login')

        except Exception as ex:
            pass

        return redirect('login')



class LoginView(View):
    def get(self, request):
        return render(request, 'authentication/login.html')

    def post(self, request):
        username = request.POST['username']
        password = request.POST['password']

        if username and password:
            user = auth.authenticate(username=username, password=password)

            if user:
                if user.is_active:
                    auth.login(request, user)
                    messages.success(request, 'Welcome, ' +
                                     user.username+' you are now logged in')
                    return redirect('expenses')
                messages.error(
                    request, 'Account is not active,please check your email')
                return render(request, 'authentication/login.html')
            messages.error(
                request, 'Invalid credentials,try again')
            return render(request, 'authentication/login.html')

        messages.error(
            request, 'Please fill all fields')
        return render(request, 'authentication/login.html')


class LogoutView(View):
    def post(self, request):
        auth.logout(request)
        messages.success(request, 'You have been logged out')
        return redirect('login')


class RequestPasswordResetEmail(View):
    def get(self, request):
        return render(request, 'authentication/reset-password.html')

    def post(self, request):
        email = request.POST['email']
        context = {
            'values': request.POST
        }
        if not validate_email(email):
            messages.error(request, _('Please provide a valid email'))
            return render(request, 'authentication/reset-password.html', context)
        
        current_site = get_current_site(request)
        user = User.objects.filter(email=email)  # Corrected this line
        if user.exists():
            email_contents = {
                'user': user[0],
                'domain': current_site.domain,
                'uid': urlsafe_base64_encode(force_bytes(user[0].pk)),
                'token': PasswordResetTokenGenerator().make_token(user[0]),
            }

            link = reverse('reset-user-password', kwargs={
                'uidb64': email_contents['uid'], 'token': email_contents['token']
            })

            email_subject = 'Reset Password'

            reset_url = 'http://'+current_site.domain+link

            email_message = EmailMessage(
                email_subject,
                'Hi, Please click the link below to reset your password:\n'+reset_url,
                'noreply@example.com',
                [email],
            )
            email_message.send(fail_silently=False)

            messages.success(request, 'An email has been sent')
            return render(request, 'authentication/reset-password.html', context)

        messages.error(request, 'No user is associated with this email')
        return render(request, 'authentication/reset-password.html', context)

# class CompletePasswordReset(View):
#     @csrf_protect
#     def get(self, request, uidb64, token):
#         context = {
#             'uidb64': uidb64,
#             'token': token
#         }
#         return render(request, 'authentication/set-newpassword.html', context)
#     @csrf_protect
#     def post(self, request, uidb64, token):
#         # Handle form submission
#         context = {
#             'uidb64': uidb64,
#             'token': token
#         }

#         password = request.POST['password']
#         password2 = request.POST['password2']

#         if password != password2:
#             messages.error(request, 'Password do not Match')
#             return render(request, 'authentication/set-newpassword.html', context)  

#         if len(password) < 6:
#             messages.error(request, 'Password must contain 6 digit')
#             return render(request, 'authentication/set-newpassword.html', context)  
        
#         try:
#             user_id = force_str(urlsafe_base64_decode(uidb64))

#             user = User.objects.get(pk=user_id)
#             user.password = password 
#             user.save()

#             messages.success(request, 'Password Saved Sucessfull. Please Login now')
#             return redirect('login')
        
#         except Exception as identifier:
#             messages.info(request, 'Something went wrong, try again')
#             return render(request, 'authentication/set-newpassword.html', context) 
        
         
#         #return render(request, 'authentication/set-newpassword.html', context)   

@method_decorator(csrf_protect, name='dispatch')
class CompletePasswordReset(View):
    def get(self, request, uidb64, token):
        context = {
            'uidb64': uidb64,
            'token': token
        }
        return render(request, 'authentication/set-newpassword.html', context)

    def post(self, request, uidb64, token):
        password = request.POST['password']
        password2 = request.POST['password2']

        context = {
            'uidb64': uidb64,
            'token': token
        }

        if password != password2:
            messages.error(request, 'Passwords do not match')
            return render(request, 'authentication/set-newpassword.html', context)

        if len(password) < 6:
            messages.error(request, 'Password must contain at least 6 characters')
            return render(request, 'authentication/set-newpassword.html', context)

        try:
            user_id = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=user_id)

            if not PasswordResetTokenGenerator().check_token(user, token):
                messages.info(request, 'Password reset link is invalid, please request a new one')
                return render(request, 'authentication/reset-password.html', context)

            user.set_password(password)
            user.save()
            messages.success(request, 'Password reset successful. Please log in.')
            return redirect('login')

        except Exception as identifier:
            messages.error(request, 'Something went wrong, please try again')
            return render(request, 'authentication/set-newpassword.html', context)
