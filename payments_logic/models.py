from decimal import Decimal

from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.db import models


class Person(models.Model):
    creator = models.ForeignKey(User, on_delete=models.CASCADE, to_field='username')

    name = models.CharField(max_length=140, null=False, editable=True)
    email = models.EmailField(null=True, editable=True)

    def __str__(self):
        return self.name


class Travel(models.Model):
    EUR = 'EUR'
    USD = 'USD'
    RUR = 'RUR'

    CURRENCIES = [
        (EUR, 'Euro'),
        (USD, 'US Dollar'),
        (RUR, 'Russian Ruble'),
    ]

    creator = models.ForeignKey(User, on_delete=models.CASCADE, to_field='username')

    title = models.CharField(max_length=100, null=False, editable=True)
    start_date = models.DateField(null=False, editable=True)
    end_date = models.DateField(null=False, editable=True)
    travelers = models.ManyToManyField(Person, editable=True)
    currency = models.CharField(max_length=3, choices=CURRENCIES, default=RUR)

    def __str__(self):
        return f'{self.title} ({str(self.start_date)} - {str(self.end_date)})'


class Payment(models.Model):
    title = models.CharField(max_length=100, null=False)
    value = models.DecimalField(null=False,
                                max_digits=9,
                                decimal_places=2,
                                validators=[MinValueValidator(Decimal('0.01'),
                                                              message='Значение должно быть больше 0.01')])

    payer = models.ForeignKey(Person, on_delete=models.CASCADE)
    travel = models.ForeignKey(Travel, on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.title} - {self.value}'


class Debt(models.Model):
    source = models.ForeignKey(Payment, on_delete=models.CASCADE)
    debitor = models.ForeignKey(Person, on_delete=models.CASCADE)
    value = models.DecimalField(null=False, max_digits=9, decimal_places=2)

    def __str__(self):
        return f'{self.debitor}s debt: {self.value} to {self.source.payer}'
