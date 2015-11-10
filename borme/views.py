from django.views.generic.list import ListView
from django.views.generic.detail import DetailView

from django.template import RequestContext
from django.shortcuts import render_to_response
from django.views.generic import TemplateView
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import Http404, HttpResponse
from django.utils.safestring import mark_safe

from .forms import LBSearchForm
from .models import Company, Person, Anuncio, Config, Borme
from .utils import LibreBormeCalendar, estimate_count_fast

from haystack.views import SearchView

import datetime
import csv


def generate_person_csv_cargos_actual(context, slug):
    person = Person.objects.get(slug=slug)
    filename = 'cargos_actuales_%s_%s' % (slug, datetime.date.today().isoformat())
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="%s.csv"' % filename

    writer = csv.writer(response)
    writer.writerow(['Cargo', 'Nombre', 'Desde'])
    for cargo in person.cargos_actuales:
        writer.writerow([cargo['title'], cargo['name'], cargo['date_from']])

    return response


def generate_person_csv_cargos_historial(context, slug):
    person = Person.objects.get(slug=slug)
    filename = 'cargos_historial_%s_%s' % (slug, datetime.date.today().isoformat())
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="%s.csv"' % filename

    writer = csv.writer(response)
    writer.writerow(['Cargo', 'Nombre', 'Desde', 'Hasta'])
    for cargo in person.cargos_historial:
        date_from = cargo.get('date_from', '')
        writer.writerow([cargo['title'], cargo['name'], date_from, cargo['date_to']])

    return response


def generate_company_csv_cargos_actual(context, slug):
    company = Company.objects.get(slug=slug)
    filename = 'cargos_actuales_%s_%s' % (slug, datetime.date.today().isoformat())
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="%s.csv"' % filename

    writer = csv.writer(response)
    writer.writerow(['Cargo', 'Nombre', 'Desde', 'Tipo'])
    for cargo in company.cargos_actuales:
        writer.writerow([cargo['title'], cargo['name'], cargo['date_from'], cargo['type']])

    return response


def generate_company_csv_cargos_historial(context, slug):
    company = Company.objects.get(slug=slug)
    filename = 'cargos_historial_%s_%s' % (slug, datetime.date.today().isoformat())
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="%s.csv"' % filename

    writer = csv.writer(response)
    writer.writerow(['Cargo', 'Nombre', 'Desde', 'Hasta', 'Tipo'])
    for cargo in company.cargos_historial:
        date_from = cargo.get('date_from', '')
        writer.writerow([cargo['title'], cargo['name'], date_from, cargo['date_to'], cargo['type']])

    return response


class HomeView(TemplateView):
    template_name = "home.html"

    def get_context_data(self, **kwargs):
        context = super(HomeView, self).get_context_data(**kwargs)

        # FIXME: performance-killer: .count()

        last_modified = Config.objects.first().last_modified.date()
        context['total_companies'] = estimate_count_fast('borme_company')  #
        context['total_persons'] = estimate_count_fast('borme_person')  #
        context['total_anuncios'] = estimate_count_fast('borme_anuncio')  #
        #context['random_companies'] = Company.objects.all().order_by('?')[:10]
        #context['random_persons'] = Person.objects.all().order_by('?')[:10]
        #context['last_modified'] = Config.objects.first().last_modified
        context['random_companies'] = Company.objects.all().order_by('-date_updated')[:10]
        context['random_persons'] = Person.objects.all().order_by('-date_updated')[:10]
        #context['random_companies'] = Company.objects.filter(date_updated=last_modified).order_by('?')[:10]
        #context['random_persons'] = Person.objects.filter(date_updated=last_modified).order_by('?')[:10]
        context['last_modified'] = last_modified

        today = datetime.date.today()
        calendar = LibreBormeCalendar().formatmonth(today.year, today.month)
        context['calendar'] = mark_safe(calendar)
        return context


class LBSearchView(SearchView):
    template = "search/search3.html"

    def __init__(self, template=None, load_all=True, form_class=LBSearchForm, searchqueryset=None, context_class=RequestContext, results_per_page=25):
        super(LBSearchView, self).__init__(template, load_all, form_class, searchqueryset, context_class, results_per_page)

    def create_response(self):
        """
        Generates the actual HttpResponse to send back to the user.
        """
        paginator_companies = Paginator(self.results['Company'], self.results_per_page)
        paginator_persons = Paginator(self.results['Person'], self.results_per_page)
        page_no = int(self.request.GET.get('page', 1))

        context = {
            'query': self.query,
            'form': self.form,
            'suggestion': None,
        }

        try:
            page_companies = paginator_companies.page(page_no)
        except PageNotAnInteger:
            page_companies = paginator_companies.page(1)
            context['page_no'] = 1
        except EmptyPage:
            page_companies = paginator_companies.page(paginator_companies.num_pages)
        finally:
            context['paginator_companies'] = paginator_companies
            pagerange = paginator_companies.page_range[:3] + paginator_companies.page_range[-3:]
            pagerange.append(page_companies.number)
            pagerange = list(set(pagerange))
            pagerange.sort()
            if len(pagerange) == 1:
                pagerange = []
            page_companies.myrange = pagerange
            context['page_companies'] = page_companies

        try:
            page_persons = paginator_persons.page(page_no)
        except PageNotAnInteger:
            page_persons = paginator_persons.page(1)
            context['page_no'] = 1
        except EmptyPage:
            page_persons = paginator_persons.page(paginator_persons.num_pages)
        finally:
            context['paginator_persons'] = paginator_persons
            pagerange = paginator_persons.page_range[:3] + paginator_persons.page_range[-3:]
            pagerange.append(page_persons.number)
            pagerange = list(set(pagerange))
            pagerange.sort()
            if len(pagerange) == 1:
                pagerange = []
            page_persons.myrange = pagerange
            context['page_persons'] = page_persons

        if self.results and hasattr(self.results, 'query') and self.results.query.backend.include_spelling:
            context['suggestion'] = self.form.get_suggestion()

        context.update(self.extra_context())
        return render_to_response(self.template, context, context_instance=self.context_class(self.request))


class BusquedaView(TemplateView):
    template_name = "busqueda.html"

    def get_context_data(self, **kwargs):
        context = super(BusquedaView, self).get_context_data(**kwargs)
        if 'q' in self.request.GET:
            page = self.request.GET.get('page', 1)
            q_companies = Company.objects.filter(name__icontains=self.request.GET['q'])
            q_companies = list(q_companies)  # Force
            companies = Paginator(q_companies, 25)
            q_persons = Person.objects.filter(name__icontains=self.request.GET['q'])
            q_persons = list(q_persons)  # Force
            persons = Paginator(q_persons, 25)

            context['page'] = page
            context['query'] = self.request.GET['q']

            try:
                pg_companies = companies.page(page)
            except PageNotAnInteger:
                # If page is not an integer, deliver first page.
                pg_companies = companies.page(1)
                context['page'] = 1
            except EmptyPage:
                # If page is out of range (e.g. 9999), deliver last page of results.
                pg_companies = companies.page(companies.num_pages)
            finally:
                context['page_companies'] = pg_companies
                context['paginator_companies'] = companies
                pagerange = companies.page_range[:3] + companies.page_range[-3:]
                pagerange.append(pg_companies.number)
                pagerange = list(set(pagerange))
                pagerange.sort()
                if len(pagerange) == 1:
                    pagerange = []
                context['page_companies'].myrange = pagerange

            try:
                pg_persons = persons.page(page)
            except PageNotAnInteger:
                pg_persons = persons.page(1)
                context['page'] = 1
            except EmptyPage:
                pg_persons = persons.page(persons.num_pages)
            finally:
                context['page_persons'] = pg_persons
                context['paginator_persons'] = persons
                pagerange = persons.page_range[:3] + persons.page_range[-3:]
                pagerange.append(pg_persons.number)
                pagerange = list(set(pagerange))
                pagerange.sort()
                if len(pagerange) == 1:
                    pagerange = []
                context['page_persons'].myrange = pagerange

        else:
            context['page_companies'] = []
            context['page_persons'] = []
            context['page'] = 1

        return context


class AnuncioView(DetailView):
    model = Anuncio
    context_object_name = 'anuncio'

    def get_object(self):
        try:
            self.anuncio = Anuncio.objects.get(id_anuncio=self.kwargs['id'], year=self.kwargs['year'])
            return self.anuncio
        except Anuncio.DoesNotExist:
            raise Http404('Anuncio does not exist')

    def get_context_data(self, **kwargs):
        context = super(AnuncioView, self).get_context_data(**kwargs)

        context['borme'] = Borme.objects.get(cve=self.anuncio.borme)
        return context


class BormeView(DetailView):
    model = Borme
    context_object_name = 'borme'

    def get_object(self):
        try:
            self.borme = Borme.objects.get(cve=self.kwargs['cve'])
            return self.borme
        except Borme.DoesNotExist:
            raise Http404('Borme does not exist')

    def get_context_data(self, **kwargs):
        context = super(BormeView, self).get_context_data(**kwargs)

        context['total_anuncios'] = self.borme.until_reg - self.borme.from_reg + 1
        context['bormes_dia'] = Borme.objects.filter(date=self.borme.date).order_by('cve')
        bormes_dia = list(context['bormes_dia'])
        bormes_dia.remove(self.borme)
        bormes_dia.sort(key=lambda b: b.province)
        context['bormes_dia'] = bormes_dia
        return context


class BormeDateView(TemplateView):
    template_name = 'borme/borme_fecha.html'

    def get_context_data(self, **kwargs):
        context = super(BormeDateView, self).get_context_data(**kwargs)

        year, month, _ = self.kwargs['date'].split('-')
        calendar = LibreBormeCalendar().formatmonth(int(year), int(month))  # TODO: LocaleHTMLCalendar(firstweekday=0, locale=None)
        #calendar = HTMLCalendar().formatyear(int(year))  # formatyearpage()

        resumen_dia = {}
        bormes = Borme.objects.filter(date=self.kwargs['date'])
        if len(bormes) > 0:
            from_reg = min([b.from_reg for b in bormes])
            until_reg = max([b.until_reg for b in bormes])
            anuncios = Anuncio.objects.filter(id_anuncio__gte=from_reg, id_anuncio__lte=until_reg)

            # FIXME: performance-killer. Guardar resultados en el modelo Borme
            from collections import Counter
            resumen_dia = Counter()
            for anuncio in anuncios:
                resumen_dia += Counter(anuncio.actos.keys())

        # TODO: Guardar la fecha en el anuncio
        context['calendar'] = mark_safe(calendar)
        context['date'] = self.kwargs['date']
        context['bormes'] = bormes
        context['resumen_dia'] = dict(resumen_dia)
        return context


class BormeProvinciaView(TemplateView):
    template_name = 'borme/borme_provincia.html'

    def get_context_data(self, **kwargs):
        context = super(BormeProvinciaView, self).get_context_data(**kwargs)
        bormes = Borme.objects.filter(province=self.kwargs['provincia'])

        year, month = 2015, 1
        calendar = LibreBormeCalendar().formatmonth(int(year), int(month))  # TODO: LocaleHTMLCalendar(firstweekday=0, locale=None)
        #calendar = HTMLCalendar().formatyear(int(year))  # formatyearpage()

        context['calendar'] = mark_safe(calendar)
        #context['date'] = self.kwargs['date']
        context['bormes'] = bormes
        context['anuncios'] = []
        return context


class CompanyView(DetailView):
    model = Company
    context_object_name = 'company'

    def get_object(self):
        try:
            self.company = Company.objects.get(slug=self.kwargs['slug'])
            return self.company
        except Company.DoesNotExist:
            raise Http404('Company does not exist')

    def get_context_data(self, **kwargs):
        context = super(CompanyView, self).get_context_data(**kwargs)

        context['anuncios'] = Anuncio.objects.filter(company=self.company).order_by('-id_anuncio')

        context['persons'] = []
        for cargo in self.company.todos_cargos_p:
            if cargo['name'] not in context['persons']:
                context['persons'].append(cargo['name'])

        context['companies'] = []
        for cargo in self.company.todos_cargos_c:
            if cargo['name'] not in context['companies']:
                context['companies'].append(cargo['name'])
        return context


class PersonView(DetailView):
    model = Person
    context_object_name = 'person'

    def get_object(self):
        try:
            self.person = Person.objects.get(slug=self.kwargs['slug'])
            return self.person
        except Person.DoesNotExist:
            raise Http404('Person does not exist')

    def get_context_data(self, **kwargs):
        context = super(PersonView, self).get_context_data(**kwargs)

        context['companies'] = []
        for cargo in self.person.todos_cargos:
            if cargo['name'] not in context['companies']:
                context['companies'].append(cargo['name'])
        return context


class PersonListView(ListView):
    model = Person
    context_object_name = 'people'
    queryset = Person.objects.all()[:100]


class CompanyListView(ListView):
    model = Company
    context_object_name = 'companies'
    queryset = Company.objects.all()[:100]


class CompanyProvinceListView(ListView):
    #model = Company
    context_object_name = 'companies'
    #queryset = Book.objects.filter(province==X).order_by('-name')
