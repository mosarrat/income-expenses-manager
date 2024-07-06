from django.shortcuts import render, redirect
from .models import Source, UserIncome
from django.core.paginator import Paginator
from userpreferences.models import UserPreference
from django.contrib import messages
from django.contrib.auth.decorators import login_required
import json
from django.contrib import messages
from django.contrib.auth.models import User
from django.http import JsonResponse, HttpResponse
import datetime
import csv
import xlwt

from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from io import BytesIO
from django.db.models import Sum
# Create your views here.

def search_income(request):
    if request.method == 'POST':
        search_str = json.loads(request.body).get('searchText')
        income = UserIncome.objects.filter(
            amount__istartswith=search_str, owner=request.user) | UserIncome.objects.filter(
            date__istartswith=search_str, owner=request.user) | UserIncome.objects.filter(
            description__icontains=search_str, owner=request.user) | UserIncome.objects.filter(
            source__icontains=search_str, owner=request.user)
        data = income.values()
        return JsonResponse(list(data), safe=False)


@login_required(login_url='/authentication/login')
def index(request):
    sources = Source.objects.all()
    income = UserIncome.objects.filter(owner=request.user)
    paginator = Paginator(income, 5)
    page_number = request.GET.get('page')
    page_obj = Paginator.get_page(paginator, page_number)
    currency = UserPreference.objects.get(user=request.user).currency
    context = {
        'income': income,
        'page_obj': page_obj,
        'currency': currency
    }
    return render(request, 'income/index.html', context)

def add_income(request):
    sources = Source.objects.all()
    context = {
        'sources': sources,
        'values': request.POST
    }
    if request.method == 'GET':
        return render(request, 'income/add_income.html', context)

    if request.method == 'POST':
        amount = request.POST['amount']

        if not amount:
            messages.error(request, 'Amount is required')
            return render(request, 'income/add_income.html', context)
        description = request.POST['description']
        date = request.POST['income_date']
        source = request.POST['source']

        if not description:
            messages.error(request, 'description is required')
            return render(request, 'income/add_income.html', context)

        UserIncome.objects.create(owner=request.user, amount=amount, date=date,
                                  source=source, description=description)
        messages.success(request, 'Record saved successfully')

        return redirect('income')


###
@login_required(login_url='/authentication/login')
def income_edit(request, id):
    income = UserIncome.objects.get(pk=id)
    sources = Source.objects.all()
    context = {
        'income': income,
        'values': income,
        'sources': sources
    }
    if request.method == 'GET':
        return render(request, 'income/edit_income.html', context)
    if request.method == 'POST':
        amount = request.POST['amount']

        if not amount:
            messages.error(request, 'Amount is required')
            return render(request, 'income/edit_income.html', context)
        description = request.POST['description']
        date = request.POST['income_date']
        source = request.POST['source']

        if not description:
            messages.error(request, 'Description is required')
            return render(request, 'income/edit_income.html', context)

        income.owner = request.user
        income.amount = amount
        income. date = date
        income.source = source
        income.description = description

        income.save()
        messages.success(request, 'Income updated  successfully')

        return redirect('income')

###
def delete_income(request, id):
    income = UserIncome.objects.get(pk=id)
    income.delete()
    messages.success(request, 'Income Record removed')
    return redirect('income')


def income_source_summary(request):
    todays_date = datetime.date.today()
    six_months_ago = todays_date - datetime.timedelta(days=30 * 6)
    userincome = UserIncome.objects.filter(owner=request.user, date__gte=six_months_ago, date__lte=todays_date)
    finalrep = {}
    
    def get_source(userincome):
        return userincome.source
    
    source_list = list(set(map(get_source, userincome)))
    
    def get_income_source_amount(source):
        amount = 0
        filtered_by_source = userincome.filter(source=source)
        for item in filtered_by_source:
            amount += item.amount
        return amount
    
    for source in source_list:
        finalrep[source] = get_income_source_amount(source)
    
    # print(finalrep)  # Print the final report to the console for debugging
    return JsonResponse({'income_source_data': finalrep}, safe=False)

def stats_view(request):
    return render(request, 'income/income_stats.html')

def export_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=Income_' + datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + '.csv'

    writer = csv.writer(response)
    writer.writerow(['Amount', 'Description', 'Source', 'Date'])

    incomes = UserIncome.objects.filter(owner=request.user)

    for income in incomes:
        writer.writerow([income.amount, income.description, income.source, income.date])
    return response

def export_excel(request):
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = 'attachment; filename=Income_' + datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + '.xls'

    wb = xlwt.Workbook(encoding= 'utf-8')
    ws = wb.add_sheet('Incomes')
    row_num = 0
    font_style = xlwt.XFStyle()
    font_style.font.bold = True

    columns = ['Amount', 'Description', 'Source', 'Date']

    for col_num in range(len(columns)):
        ws.write(row_num, col_num, columns[col_num], font_style)
    
    font_style = xlwt.XFStyle()
    rows = UserIncome.objects.filter(owner=request.user).values_list('amount', 'description', 'source', 'date')

    for row in rows:
        row_num+=1

        for col_num in range(len(row)):
            ws.write(row_num, col_num, str(row[col_num]), font_style)

    wb.save(response)

    return response

def export_pdf(request):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename=Income_' + datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + '.pdf'
    
    incomes = UserIncome.objects.filter(owner=request.user)
    total_amount = incomes.aggregate(Sum('amount'))['amount__sum'] or 0

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4


    # # Title
    # p.setFont("Helvetica-Bold", 16)
    # p.drawString(100, height - 100, "income List")

    # Title
    title_text = "Income List"
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
    p.drawString(200, height - 150, "Source")
    p.drawString(300, height - 150, "Description")
    p.drawString(450, height - 150, "Date")

    # Table Rows
    p.setFont("Helvetica", 12)
    y = height - 180
    for i, income in enumerate(incomes):
        p.drawString(50, y, str(i + 1))
        p.drawString(100, y, str(income.amount))
        p.drawString(200, y, income.source)
        p.drawString(300, y, income.description)
        p.drawString(450, y, income.date.strftime("%Y-%m-%d"))
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
