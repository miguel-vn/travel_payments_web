from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import AnonymousUser
from django.db import connection
from django.db.models import Sum, Q, F
from django.shortcuts import reverse, HttpResponseRedirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DetailView, ListView

import payments_logic.service_functions as sf
from payments_logic.models import Travel, Debt
from .forms import TravelForm, PersonForm, PaymentForm


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
        travels = Travel.objects.filter(creator=self.request.user).order_by('-start_date', '-end_date')
        single_current = travels.filter(start_date__lte=timezone.now(), end_date__gte=timezone.now())

        if len(single_current) == 1:
            travel_id = single_current[0].id
            return HttpResponseRedirect(reverse('travel_detail', args=[travel_id]))

        return travels


class TravelDetail(LoginRequiredMixin, DetailView):
    login_url = reverse_lazy('login')

    model = Travel
    template_name = 'travel_details.html'
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


class AddPayment(LoginRequiredMixin, CreateView):
    login_url = reverse_lazy('login')

    template_name = 'new_payment.html'
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


class CreateTravel(LoginRequiredMixin, CreateView):
    login_url = reverse_lazy('login')

    template_name = 'new_travel.html'
    form_class = TravelForm

    def form_valid(self, form):
        travel_data = form.save(commit=False)
        travel_data.creator = self.request.user
        travel_data.save()
        travel_data.travelers.add(*form.cleaned_data.get('travelers'))
        travel_data.save()

        return HttpResponseRedirect(reverse('travel_detail', args=[travel_data.id]))


class NewPerson(LoginRequiredMixin, CreateView):
    login_url = reverse_lazy('login')

    template_name = 'new_person.html'
    form_class = PersonForm
    success_url = reverse_lazy('new_travel')

    def form_valid(self, form):
        user_data = form.save(commit=False)
        user_data.creator = self.request.user
        user_data.save()

        return HttpResponseRedirect(reverse('new_travel'))
