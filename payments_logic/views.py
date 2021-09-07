from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import AnonymousUser, User
from django.db import connection
from django.db.models import Sum, Q, F
from django.shortcuts import reverse, HttpResponseRedirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DetailView, ListView, UpdateView, DeleteView, FormView

import payments_logic.service_functions as sf
from payments_logic.models import Travel, Debt, Payment, Friendship
from .forms import TravelForm, PersonForm, PaymentForm
import uuid


def about_page(request):
    return render(request, 'about.html')


class TravelsList(ListView):  # LoginRequiredMixin, ListView):
    model = Travel
    paginate_by = 10
    template_name = 'travels_list.html'
    context_object_name = 'travels'

    def get_queryset(self):
        if isinstance(self.request.user, AnonymousUser):
            return []
        travels = Travel.objects.filter(travelers__username=self.request.user.username).order_by('-start_date', '-end_date')
        # single_current = travels.filter(start_date__lte=timezone.now(), end_date__gte=timezone.now())
        # if len(list(single_current)) == 1:
        #     travel_id = single_current[0].id
        #     return HttpResponseRedirect(reverse('travel_detail', args=[travel_id]))

        return travels


class TravelDetail(LoginRequiredMixin, DetailView):
    login_url = reverse_lazy('login')

    model = Travel
    template_name = 'travels/travel_details.html'
    context_object_name = 'travel'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = '''
            select pa.id, pr.name, pa.title as title, pa.value as value, group_concat(pr2.name, ", ") as debitors 
            from payments_logic_payment pa
            inner join payments_logic_person pr on pr.id = pa.payer_id
            left join payments_logic_debt d on d.source_id = pa.id
            left join payments_logic_person pr2 on pr2.id = d.debitor_id
            where pa.travel_id = %s
            group by pa.id, pr.name''' % kwargs.get('object').id

        with connection.cursor() as cur:
            cur.execute(query)
            context['payments_list'] = sf.dictfetchall(cur)

        return context


class BaseOperations(LoginRequiredMixin):
    login_url = reverse_lazy('login')


class AddPayment(BaseOperations, CreateView):
    template_name = 'payments/new_payment.html'
    form_class = PaymentForm
    success_url = reverse_lazy('travel_detail')

    def get_form_kwargs(self, *args, **kwargs):
        form_kwargs = super(AddPayment, self).get_form_kwargs()
        form_kwargs.update({'travel_id': self.kwargs['travel_pk']})

        return form_kwargs

    def form_valid(self, form):
        travel = Travel.objects.get(pk=self.kwargs['travel_pk'])

        payment_data = form.save(commit=False)
        payment_data.travel_id = travel.id
        payment_data.payer = form.cleaned_data['payer']

        payment_data.save()

        debitors = form.cleaned_data['debitors'].filter(~Q(id=payment_data.payer.id))

        if debitors:
            value = payment_data.value / (len(debitors) + 1)

            Debt.objects.bulk_create(
                objs=[Debt(source=payment_data,
                           value=0 - value,
                           debitor=payment_data.payer)] + [
                         Debt(source=payment_data,
                              value=value,
                              debitor=debitor) for debitor in debitors])

        return HttpResponseRedirect(reverse('travel_detail', args=[travel.id]))


class UpdatePayment(BaseOperations, UpdateView):
    template_name = 'payments/payment_update.html'
    model = Payment
    form_class = PaymentForm

    def get_form_kwargs(self, *args, **kwargs):
        form_kwargs = super(UpdatePayment, self).get_form_kwargs()
        form_kwargs.update({'travel_id': self.kwargs['travel_pk']})
        form_kwargs.update({'source_id': self.kwargs['source_id']})

        return form_kwargs

    form_valid = AddPayment.form_valid

    def get_success_url(self):
        return reverse('travel_detail', kwargs={'pk': self.kwargs['pk']})


class DeletePayment(BaseOperations, DeleteView):
    model = Payment
    template_name = 'payments/payment_confirm_delete.html'

    def get_success_url(self):
        return reverse('travel_detail', kwargs={'pk': self.kwargs['pk']})


class SummaryPaymentsAndDebts(TravelDetail):
    # TODO Продумать возможность сокращения цепочки долгов (например Ксюша - я - Вова = Ксюша - Вова)
    template_name = 'summary.html'
    context_object_name = 'summary'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        summary = sf.get_summary(Debt.objects
                                 .filter(source__travel_id=kwargs.get('object').id)
                                 .values('debitor__name', 'source__payer__name')
                                 .filter(~Q(debitor__name=F('source__payer__name')))
                                 .annotate(total=Sum('value')))

        context['summary'] = summary

        return context


class CreateTravel(BaseOperations, CreateView):
    template_name = 'travels/new_travel.html'
    form_class = TravelForm

    def get_form_kwargs(self, *args, **kwargs):
        form_kwargs = super(CreateTravel, self).get_form_kwargs()
        form_kwargs.update({'current_user': self.request.user.username})
        return form_kwargs

    def form_valid(self, form):
        print('form', form.data)
        travel_data = form.save(commit=False)
        print('travel_data', travel_data)
        travel_data.creator = User.objects.get(username=self.request.user.username)
        travel_data.save()
        print('form.cleaned_data', form.cleaned_data)
        travel_data.travelers.add(*form.cleaned_data.get('travelers'))
        print('travel_data2', travel_data)
        travel_data.save()

        return HttpResponseRedirect(reverse('travel_detail', args=[travel_data.id]))


class UpdateTravel(BaseOperations, UpdateView):
    template_name = 'travels/travel_update.html'
    model = Travel
    form_class = TravelForm

    def get_success_url(self):
        return reverse('travel_detail', kwargs={'pk': self.kwargs['pk']})


class DeleteTravel(BaseOperations, DeleteView):
    model = Travel
    template_name = 'travels/travel_confirm_delete.html'
    success_url = reverse_lazy('travels_list')


class NewPerson(BaseOperations, FormView):
    template_name = 'new_person.html'
    form_class = PersonForm
    success_url = reverse_lazy('new_travel')

    def form_valid(self, form):
        form_data = form.cleaned_data
        email = form_data.get('email', None)
        name = form_data.get('name')
        if email:
            username = email[:email.index('@')]
        else:
            username = name + str(uuid.uuid4())[:8]

        creator = User.objects.get(username=self.request.user.username)

        existing_user = User.objects.filter(email=email)
        if not existing_user:
            existing_user = User.objects.create_user(username=username, first_name=name, email=email)
            existing_user.save()
        else:
            existing_user = existing_user[0]

        new_friendship = Friendship(creator=creator, friend=existing_user)
        new_friendship.save()

        return HttpResponseRedirect(reverse('new_travel'))
