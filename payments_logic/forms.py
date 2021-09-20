from django import forms
from django.contrib.auth.models import User
from django.db.models import Q

from .models import Travel, Payment, Friendship


class PersonForm(forms.Form):
    name = forms.CharField(max_length=140)
    email = forms.EmailField(required=True)

    widgets = {'name': forms.TextInput(),
               'email': forms.EmailInput()}
    labels = {'name': 'Имя',
              'email': 'email'}


class UserChoiseField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.get_full_name()  # f'{obj.first_name} {obj.last_name}'


class UserMultipleChoiseField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        return obj.get_full_name()


class TravelForm(forms.ModelForm):
    class Meta:
        model = Travel
        fields = ('title', 'start_date', 'end_date')
        labels = {'start_date': 'Дата старта',
                  'end_date': 'Дата окончания',
                  'title': 'Что за поездка?'}
        widgets = {'start_date': forms.DateInput(attrs={'type': 'date'}),
                   'end_date': forms.DateInput(attrs={'type': 'date'}),
                   'title': forms.TextInput(attrs={'placeholder': 'Title of your travel'})}

    def __init__(self, **kwargs):
        current_user = kwargs.pop('current_user')
        super(TravelForm, self).__init__(**kwargs)

        friends_ids = Friendship.objects.filter(creator__username=current_user).values_list('friend__username')

        self.fields['travelers'] = UserMultipleChoiseField(
            User.objects.filter(Q(username__in=friends_ids) | Q(username=current_user)),
            label='Кто едет?',
            widget=forms.CheckboxSelectMultiple(),
            to_field_name='username')

    def clean(self):
        super(TravelForm, self).clean()
        start_date = self.cleaned_data.get("start_date")
        end_date = self.cleaned_data.get("end_date")
        if end_date < start_date:
            msg = "Указаны некорректные даты: дата начала больше даты окончания."
            self._errors["date_validation"] = self.error_class([msg])


class PaymentForm(forms.ModelForm):

    def __init__(self, **kwargs):
        travel_id = kwargs.pop('travel_id')
        super(PaymentForm, self).__init__(**kwargs)
        travelers = Travel.objects.get(pk=travel_id).travelers.all()
        self.fields['payer'] = UserChoiseField(travelers, label='Кто платит?', widget=forms.RadioSelect())
        self.fields['debitors'] = UserMultipleChoiseField(travelers,
                                                          label='На кого разделить счет?',
                                                          widget=forms.CheckboxSelectMultiple(),
                                                          required=False)

    class Meta:
        model = Payment
        fields = ('title', 'value')

        widgets = {'title': forms.TextInput(), }  # attrs={'placeholder': 'Title of payment'}),

        labels = {'title': 'Что оплатили?',
                  'value': 'Сколько?', }
