from django.db.models import Q
from django_filters import rest_framework as filters

from .models import Document


class DocumentFilter(filters.FilterSet):
    q = filters.CharFilter(method="filter_q")
    tag = filters.CharFilter(method="filter_tag")  # supports multiple tag params
    folder = filters.NumberFilter(field_name="folder_id")
    processed = filters.BooleanFilter(field_name="is_processed")
    created_after = filters.DateFilter(field_name="created_at", lookup_expr="gte")
    created_before = filters.DateFilter(field_name="created_at", lookup_expr="lte")

    class Meta:
        model = Document
        fields = ["q", "tag", "folder", "processed", "created_after", "created_before"]

    def filter_q(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(
            Q(title__icontains=value)
            | Q(original_filename__icontains=value)
            | Q(content_text__icontains=value)
        )

    def filter_tag(self, queryset, name, value):
        # value is handled one at a time; allow repeated 'tag' params
        values = self.request.query_params.getlist("tag") if hasattr(self.request, "query_params") else [value]
        if not values:
            return queryset
        return queryset.filter(tags__name__in=values).distinct()


