""" REST views for the query API
"""

from django.core.urlresolvers import reverse

from core_explore_common_app.components.result.models import Result
from core_explore_common_app.rest.result.serializers import ResultSerializer
from core_explore_common_app.utils.result import result as result_utils
from core_main_app.rest.data.abstract_views import AbstractExecuteLocalQueryView
from core_main_app.utils.pagination.rest_framework_paginator.pagination import StandardResultsSetPagination


class ExecuteLocalQueryView(AbstractExecuteLocalQueryView):
    def build_response(self, data_list):
        """ Build the paginated response.

        Args:
            data_list: List of data.

        Returns:
            The response.

        """
        # get paginator
        paginator = StandardResultsSetPagination()
        # get requested page from list of results
        page = paginator.paginate_queryset(data_list, self.request)

        # FIXME: See if can use reverse to include data id, and avoid format
        # Get detail view base url (to be completed with data id)
        detail_url_base = reverse("core_main_app_data_detail")
        url_access_data = reverse("core_explore_common_app_get_result_from_data_id")

        # Build list of results
        results = []
        # Template info
        template_info = dict()
        for data in page:
            # get data's template
            template = data.template
            # get and store data's template information
            if template not in template_info:
                template_info[template] = result_utils.get_template_info(template)

            results.append(Result(title=data.title,
                                  xml_content=data.xml_content,
                                  template_info=template_info[template],
                                  detail_url="{0}?id={1}".format(detail_url_base, str(data.id)),
                                  access_data_url="{0}?id={1}".format(url_access_data,
                                                                      str(data.id))
                                  )
                           )

        # serialize results
        serialized_results = ResultSerializer(results, many=True)
        # return http response
        return paginator.get_paginated_response(serialized_results.data)
