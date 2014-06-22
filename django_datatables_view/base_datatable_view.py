# -*- coding: utf-8 -*-
import re

from .mixins import JSONResponseView


class DatatableMixin(object):
    """ JSON data for datatables
    """
    model = None
    columns = []
    order_columns = []
    max_display_length = 100  # max limit of records returned, do not allow to kill our server by huge sets of data

    def initialize(*args, **kwargs):
        pass

    def get_order_columns(self):
        """ Return list of columns used for ordering
        """
        return self.order_columns

    def get_columns(self):
        """ Returns the list of columns that are returned in the result set
        """
        return self.columns

    def render_column(self, row, column):
        """ Renders a column on a row
        """
        if hasattr(row, 'get_%s_display' % column):
            # It's a choice field
            text = getattr(row, 'get_%s_display' % column)()
        else:
            try:
                text = getattr(row, column)
            except AttributeError:
                obj = row
                for part in column.split('.'):
                    if obj is None:
                        break
                    obj = getattr(obj, part)

                text = obj

        if hasattr(row, 'get_absolute_url'):
            return '<a href="%s">%s</a>' % (row.get_absolute_url(), text)
        else:
            return text

    def ordering(self, qs):
        """ Get parameters from the request and prepare order by clause
        """
        request = self.request
        # Number of columns that are used in sorting
        try:
            sorting_cols = len(
                [(key, value) for key, value in self.request.POST.iteritems() if re.search(r'order.\d+..column.', key)]
            )
        except ValueError:
            sorting_cols = 0

        order = []
        order_columns = self.get_order_columns()

        for i in range(sorting_cols):
            # sorting column
            try:
                sort_col = int(request.REQUEST.get('order[%s][column]' % i))
            except ValueError:
                sort_col = 0

            # sorting order
            sort_dir = request.REQUEST.get('order[%s][dir]' % i)
            sdir = '-' if sort_dir == 'desc' else ''
            sortcol = order_columns[sort_col]

            if isinstance(sortcol, list):
                for sc in sortcol:
                    order.append('%s%s' % (sdir, sc.replace('.', '__')))
            else:
                order.append('%s%s' % (sdir, sortcol.replace('.', '__')))
        if order:
            return qs.order_by(*order)
        return qs

    def paging(self, qs):
        """ Paging
        """
        limit = min(int(self.request.REQUEST.get('length', 10)), self.max_display_length)
        
        # if pagination is disabled ("paging": false)
        if limit == -1:
            return qs
        
        start = int(self.request.REQUEST.get('start', 0))
        offset = start + limit
        
        return qs[start:offset]

    def get_initial_queryset(self):
        if not self.model:
            raise NotImplementedError("Need to provide a model or implement get_initial_queryset!")
        return self.model.objects.all()

    def filter_queryset(self, qs):
        return qs

    def prepare_results(self, qs):
        data = []
        for item in qs:
            data.append([self.render_column(item, column) for column in self.get_columns()])
        return data

    def get_context_data(self, *args, **kwargs):
        request = self.request
        self.initialize(*args, **kwargs)

        qs = self.get_initial_queryset()

        # number of records before filtering
        total_records = qs.count()

        qs = self.filter_queryset(qs)

        # number of records after filtering
        total_display_records = qs.count()

        qs = self.ordering(qs)
        qs = self.paging(qs)

        # prepare output data
        aaData = self.prepare_results(qs)

        ret = {'draw': int(request.REQUEST.get('draw', 0)),
               'iTotalRecords': total_records,
               'iTotalDisplayRecords': total_display_records,
               'data': aaData
               }

        return ret


class BaseDatatableView(DatatableMixin, JSONResponseView):
    pass
