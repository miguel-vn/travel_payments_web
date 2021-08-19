from django.db import connection
from django.db.models import Sum
from django.shortcuts import reverse, HttpResponseRedirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView

from payments_logic.models import Travel, Debt
from .forms import TravelForm, PersonForm, PaymentForm


def get_summary(data):
    new_data = []

    for row in data:

        deb_name = row['debitor__name']
        payer = row['source__payer__name']
        initial_value = row['total']
        added = False

        for another_row in data:
            if another_row['debitor__name'] == deb_name and another_row['source__payer__name'] == payer:
                continue
            if another_row['debitor__name'] == payer and another_row['source__payer__name'] == deb_name:
                if another_row['total'] > initial_value:
                    new_row = {'debitor__name': deb_name,
                               'source__payer__name': payer,
                               'total': another_row['total'] - initial_value}
                elif another_row['total'] < initial_value:
                    new_row = {'debitor__name': deb_name,
                               'source__payer__name': payer,
                               'total': another_row['total'] - initial_value}
                else:
                    continue
                new_data.append(new_row)
                added = True

        if not added:
            new_data.append(row)

    new_data = list(filter(lambda elem: elem['total'] > 0, new_data))
    return new_data


def about_page(request):
    return render(request, 'about.html')


class TravelsList(ListView):
    model = Travel
    paginate_by = 10
    template_name = 'travels_list.html'
    context_object_name = 'travels'
    ordering = ['-start_date', '-end_date']


def dictfetchall(cursor):
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]


class TravelDetail(DetailView):
    model = Travel
    template_name = 'travel_details.html'
    context_object_name = 'travel'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = '''
            select d.source_id, pa.title as title, pa.value as value, group_concat(pr.name, ", ") as debitors from payments_logic_debt d
            inner join payments_logic_payment pa on d.source_id = pa.id
            inner join payments_logic_person pr on pr.id = d.debitor_id
            where pa.travel_id = %s
            group by d.source_id''' % kwargs.get('object').id

        with connection.cursor() as cur:
            cur.execute(query)
            context['payments_list'] = dictfetchall(cur)

        return context


class AddPayment(CreateView):
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
        debitors = form.cleaned_data['debitors'].distinct()

        if debitors:
            value = payment_data.value / (len(debitors) + 1)

            Debt.objects.bulk_create(
                objs=[Debt(source=payment_data,
                           value=0 - value,
                           debitor=payment_data.payer)] + [
                         Debt(source=payment_data,
                              value=value,
                              debitor=debitor) for debitor in debitors if debitor != payment_data.payer])

        return HttpResponseRedirect(reverse('travel_detail', args=[travel.id]))


class SummaryPaymentsAndDebts(TravelDetail):
    template_name = 'summary.html'
    context_object_name = 'summary'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        summary = get_summary(Debt.objects
                              .filter(source__travel_id=kwargs.get('object').id)
                              .values('debitor__name', 'source__payer__name')
                              .annotate(total=Sum('value')))

        context['summary'] = summary

        return context


class CreateTravel(CreateView):
    template_name = 'new_travel.html'
    form_class = TravelForm
    success_url = '/'


class NewPerson(CreateView):
    template_name = 'new_person.html'
    form_class = PersonForm
    success_url = reverse_lazy('new_travel')