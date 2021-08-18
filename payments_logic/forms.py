from django import forms

from .models import Travel, Person, Payment


class PersonForm(forms.ModelForm):
    class Meta:
        model = Person
        fields = ('name',)
        widgets = {'name': forms.TextInput()}
        labels = {'name': 'Имя'}


class TravelForm(forms.ModelForm):
    class Meta:
        model = Travel
        fields = ('title', 'start_date', 'end_date', 'travelers')

        widgets = {'start_date': forms.DateInput(attrs={'type': 'date'}),
                   'end_date': forms.DateInput(attrs={'type': 'date'}),
                   'title': forms.TextInput(attrs={'placeholder': 'Title of your travel'}),
                   'travelers': forms.CheckboxSelectMultiple()}

        labels = {'title': 'Что за поездка?',
                  'start_date': 'Дата старта',
                  'end_date': 'Дата окончания',
                  'travelers': 'Кто едет?'}


class PaymentForm(forms.ModelForm):

    def __init__(self, **kwargs):
        travel_id = kwargs.pop('travel_id')
        super(PaymentForm, self).__init__(**kwargs)
        travelers = Travel.objects.get(pk=travel_id).travelers.all()
        self.fields['payer'] = forms.ModelChoiceField(travelers, label='Кто платит?', widget=forms.RadioSelect())
        self.fields['debitors'] = forms.ModelMultipleChoiceField(travelers,
                                                                 label='На кого разделить счет?',
                                                                 widget=forms.CheckboxSelectMultiple())

    class Meta:
        model = Payment
        fields = ('title', 'value')

        widgets = {'title': forms.TextInput(), }  # attrs={'placeholder': 'Title of payment'}),

        labels = {'title': 'Что оплатили?',
                  'value': 'Сколько?', }
