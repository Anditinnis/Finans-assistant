from django import forms
from .models import Category, Transaction


class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['category', 'amount', 'date', 'comment']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'comment': forms.TextInput(attrs={'placeholder': 'Например: обед в кафе'}),
        }
        labels = {
            'category': 'Категория',
            'amount': 'Сумма (₽)',
            'date': 'Дата',
            'comment': 'Комментарий',
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user:
            self.fields['category'].queryset = Category.objects.filter(user=self.user)
            self.fields['category'].empty_label = '— выбери категорию —'

    def clean_category(self):
        category = self.cleaned_data['category']
        if self.user and category.user != self.user:
            raise forms.ValidationError('Нельзя использовать чужую категорию')
        return category


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'type', 'icon', 'color']
        widgets = {
            'color': forms.TextInput(attrs={'type': 'color'}),
        }
        labels = {
            'name': 'Название',
            'type': 'Тип',
            'icon': 'Иконка (эмодзи)',
            'color': 'Цвет',
        }