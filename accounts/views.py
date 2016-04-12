from django.shortcuts import render, redirect
from django.contrib import messages,auth
from accounts.forms import UserRegistrationForm, UserLoginForm
from django.core.urlresolvers import reverse
from django.template.context_processors import csrf
from django.contrib.auth.decorators import login_required
from django.conf import settings
import datetime, stripe, arrow, json
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from models import User


stripe.api_key = settings.STRIPE_SECRET

#Create your views here.

def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        print form

        if form.is_valid():
            try:
                customer = stripe.Customer.create(
                    description=form.cleaned_data['email'],
                    card=form.cleaned_data['stripe_id'],
                    plan='REG_MONTHLY'
                )
                print customer
            except stripe.CardError:
                messages.error(request, "Your card was declined!")
                print 'error carderror'
            if customer:
                user = form.save()
                user.stripe_id = customer.id
                user.subscription_end = arrow.now().replace(weeks=+4).datetime
                user.save()

                user = auth.authenticate(email=request.POST.get('email'),
                                         password=request.POST.get('password1'))

                if user:
                    auth.login(request, user)
                    messages.success(request, "You have successfully registered!")
                    return redirect(reverse('profile'))

                else:
                    messages.error(request, "Unable to log you in at this time")
            else:
                messages.error(request, "Unable to take a payment with that card")

    else:
        today = datetime.date.today()
        form = UserRegistrationForm(initial={'expiry_month': today.month,
                                            'expiry_year': today.year})

    args = {'form': form, 'publishable': settings.STRIPE_PUBLISHABLE}
    args.update(csrf(request))

    return render(request, 'register.html', args)


# def register(request):
#     if request.method == 'POST':
#         form = UserRegistrationForm(request.POST)
#         print form.is_valid
#         #if form.is_valid():
#
#         try:
#             customer = stripe.Charge.create(
#                 amount=499,
#                 currency='USD',
#                 description=form.cleaned_data['email'],
#                 card=form.cleaned_data['stripe_id'],
#             )
#         except stripe.error.CardError, e:
#             messages.error(request, 'Your card was declined')
#
#         if customer.paid:
#
#             form.save()
#
#             user = auth.authenticate(email=request.POST.get('email'), password=request.POST.get('password1'))
#
#             if user:
#                 auth.login(request, user)
#                 messages.success(request, 'You have successfully registered')
#                 return redirect(reverse('profile'))
#
#             else:
#                 messages.error(request, 'Unable to log you in at this time ')
#         else:
#             messages.error(request, 'Unable to take payment with that card')
#
#     else:
#         today = datetime.date.today()
#         form = UserRegistrationForm()
#
#     args = {'form': form, 'publishable': settings.STRIPE_PUBLISHABLE}
#     args.update(csrf(request))
#
#     return render(request, 'register.html', args)

@login_required(login_url='/login/')
def profile(request):
    return render(request, 'profile.html', )


def login(request):
    if request.method == 'POST':
        form = UserLoginForm(request.POST)
        if form.is_valid():

            user = auth.authenticate(email=request.POST.get('email'),
                                     password=request.POST.get('password'))

            if user is not None:
                auth.login(request, user)
                messages.success(request, "You have successfully logged in!")
                return redirect(reverse('profile'))

            else:
                form.add_error(None, "Your email or password was not recognised")

    else:
        form = UserLoginForm()

    args = {'form': form}
    args.update(csrf(request))

    return render(request, 'login.html', args)


def logout(request):
    auth.logout(request)
    messages.success(request, 'You have successfully logged out')
    return redirect(reverse('index'))


@login_required(login_url='/accounts/login')
def cancel_subscription(request):
    try:
        customer = stripe.Customer.retrieve(request.user.stripe_id)
        customer.cancel_subscription(at_period_end=True)
    except Exception, e:
        messages.error(request, e)
    return redirect('profile')



@csrf_exempt
def subscriptions_webhook(request):
    event_json = json.loads(request.body)
    # verify the event by fetching it from stripe
    try:
        # first verify this is a real event from strip
        # NOTE: this will not work when testing on localhost
        # event = stripe.Event.retrieve(event_json['object']['id'])
        cust = event_json['object']['customer']
        paid = event_json['object']['paid']
        user = User.objects.get(stripe_id=cust)
        if user and paid:
            user.subscription_end = arrow.now().replace(weeks=+4).datetime
            user.save()

    except stripe.InvalidRequestError, e:
        return HttpResponse(status=404)

    return HttpResponse(status=200)


