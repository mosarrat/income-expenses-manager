from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Category, Expense
# Create your views here.
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.paginator import Paginator
import json
from django.http import JsonResponse, HttpResponse
from userpreferences.models import UserPreference
import datetime
import csv
import xlwt

# from django.template.loader import render_to_string
# from weasyprint import HTML
# import tempfile
# from django.db.models import Sum

from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from io import BytesIO
from django.db.models import Sum



def search_expenses(request):
    if request.method == 'POST':
        search_str = json.loads(request.body).get('searchText')
        expenses = Expense.objects.filter(
            amount__istartswith=search_str, owner=request.user) | Expense.objects.filter(
            date__istartswith=search_str, owner=request.user) | Expense.objects.filter(
            description__icontains=search_str, owner=request.user) | Expense.objects.filter(
            category__icontains=search_str, owner=request.user)
        data = expenses.values()
        return JsonResponse(list(data), safe=False)


@login_required(login_url='/authentication/login')
def index(request):
    categories = Category.objects.all()
    expenses = Expense.objects.filter(owner=request.user)
    paginator = Paginator(expenses, 5)
    page_number = request.GET.get('page')
    page_obj = Paginator.get_page(paginator, page_number)
    
    try:
        currency = UserPreference.objects.get(user=request.user).currency
    except UserPreference.DoesNotExist:
        currency = 'USD'  # You can set this to a default currency or handle it as needed
    
    context = {
        'expenses': expenses,
        'page_obj': page_obj,
        'currency': currency
    }
    return render(request, 'expenses/index.html', context)


@login_required(login_url='/authentication/login')
def add_expense(request):
    categories = Category.objects.all()
    context = {
        'categories': categories,
        'values': request.POST
    }
    if request.method == 'GET':
        return render(request, 'expenses/add_expenses.html', context)

    if request.method == 'POST':
        amount = request.POST['amount']

        if not amount:
            messages.error(request, 'Amount is required')
            return render(request, 'expenses/add_expenses.html', context)
        description = request.POST['description']
        date = request.POST['expense_date']
        category = request.POST['category']

        if not description:
            messages.error(request, 'description is required')
            return render(request, 'expenses/add_expenses.html', context)

        Expense.objects.create(owner=request.user, amount=amount, date=date,
                               category=category, description=description)
        messages.success(request, 'Expense saved successfully')

        return redirect('expenses')


@login_required(login_url='/authentication/login')
def expense_edit(request, id):
    expense = Expense.objects.get(pk=id)
    categories = Category.objects.all()
    context = {
        'expense': expense,
        'values': expense,
        'categories': categories
    }
    if request.method == 'GET':
        return render(request, 'expenses/edit_expenses.html', context)
    if request.method == 'POST':
        amount = request.POST['amount']

        if not amount:
            messages.error(request, 'Amount is required')
            return render(request, 'expenses/edit_expenses.html', context)
        description = request.POST['description']
        date = request.POST['expense_date']
        category = request.POST['category']

        if not description:
            messages.error(request, 'description is required')
            return render(request, 'expenses/edit_expenses.html', context)

        expense.owner = request.user
        expense.amount = amount
        expense. date = date
        expense.category = category
        expense.description = description

        expense.save()
        messages.success(request, 'Expense updated  successfully')

        return redirect('expenses')


def delete_expense(request, id):
    expense = Expense.objects.get(pk=id)
    expense.delete()
    messages.success(request, 'Expense removed')
    return redirect('expenses')


def expense_category_summary(request):
    todays_date = datetime.date.today()
    # print(todays_date)
    six_months_ago = todays_date - datetime.timedelta(days=30 * 6)
    # print(six_months_ago)
    expenses = Expense.objects.filter(owner=request.user, date__gte=six_months_ago, date__lte=todays_date)
    # print(expenses)
    number_of_rows = expenses.count()
    # print("Number of rows:", number_of_rows)
    # Initialize an empty dictionary to store category-wise totals
    finalrep = {}
    
    # Helper function to extract category from an expense object
    def get_category(expense):
        return expense.category
    
    # Create a set of unique categories from expenses
    category_list = list(set(map(get_category, expenses)))
    # print(category_list)
    # Helper function to calculate total amount for a specific category
    def get_expense_category_amount(category):
        amount = 0
        filtered_by_category = expenses.filter(category=category)
        # print(filtered_by_category)
        for item in filtered_by_category:
            amount += item.amount
        # print(amount)
        return amount
    
    # Populate finalrep dictionary with category-wise totals
    for category in category_list:
        finalrep[category] = get_expense_category_amount(category)
    # print(finalrep)
    # Return JSON response with category-wise totals
    return JsonResponse({'expense_category_data': finalrep}, safe=False)


def stats_view(request):
    return render(request, 'expenses/stats.html')


def export_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=Expenses_' + datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + '.csv'

    writer = csv.writer(response)
    writer.writerow(['Amount', 'Description', 'Category', 'Date'])

    expenses = Expense.objects.filter(owner=request.user)

    for expense in expenses:
        writer.writerow([expense.amount, expense.description, expense.category, expense.date])
    return response

def export_excel(request):
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = 'attachment; filename=Expenses_' + datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + '.xls'

    wb = xlwt.Workbook(encoding= 'utf-8')
    ws = wb.add_sheet('Expenses')
    row_num = 0
    font_style = xlwt.XFStyle()
    font_style.font.bold = True

    columns = ['Amount', 'Description', 'Category', 'Date']

    for col_num in range(len(columns)):
        ws.write(row_num, col_num, columns[col_num], font_style)
    
    font_style = xlwt.XFStyle()
    rows = Expense.objects.filter(owner=request.user).values_list('amount', 'description', 'category', 'date')

    for row in rows:
        row_num+=1

        for col_num in range(len(row)):
            ws.write(row_num, col_num, str(row[col_num]), font_style)

    wb.save(response)

    return response


def export_pdf(request):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename=Expenses_' + datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + '.pdf'
    
    expenses = Expense.objects.filter(owner=request.user)
    total_amount = expenses.aggregate(Sum('amount'))['amount__sum'] or 0

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4


    # # Title
    # p.setFont("Helvetica-Bold", 16)
    # p.drawString(100, height - 100, "Expense List")

    # Title
    title_text = "Expense List"
    title_width = p.stringWidth(title_text, "Helvetica-Bold", 16)
    title_x = (width - title_width) / 2  # Centered horizontally

    p.setFont("Helvetica-Bold", 16)
    p.drawString(title_x, height - 100, title_text)

    # Draw underline
    underline_start = title_x
    underline_end = title_x + title_width
    p.line(underline_start, height - 105, underline_end, height - 105)

    # Table Headers
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, height - 150, "No.")
    p.drawString(100, height - 150, "Amount")
    p.drawString(200, height - 150, "Category")
    p.drawString(300, height - 150, "Description")
    p.drawString(450, height - 150, "Date")

    # Table Rows
    p.setFont("Helvetica", 12)
    y = height - 180
    for i, expense in enumerate(expenses):
        p.drawString(50, y, str(i + 1))
        p.drawString(100, y, str(expense.amount))
        p.drawString(200, y, expense.category)
        p.drawString(300, y, expense.description)
        p.drawString(450, y, expense.date.strftime("%Y-%m-%d"))
        y -= 20
        if y < 100:
            p.showPage()
            y = height - 100

    # Total Amount
    p.drawString(50, y - 20, "Total")
    p.drawString(100, y - 20, str(total_amount))

    p.showPage()
    p.save()

    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    return response