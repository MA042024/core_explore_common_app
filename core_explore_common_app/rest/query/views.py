""" REST views for the query API
"""
import logging
import pytz
from django.urls import reverse

from core_explore_common_app import settings
from core_explore_common_app.components.result.models import Result
from core_explore_common_app.rest.result.serializers import ResultSerializer
from core_explore_common_app.utils.result import result as result_utils
from core_main_app.commons.exceptions import ApiError
from core_main_app.rest.data.abstract_views import AbstractExecuteLocalQueryView
from core_main_app.utils.pagination.rest_framework_paginator.pagination import (
    StandardResultsSetPagination,
)

logger = logging.getLogger(__name__)


class ExecuteLocalQueryView(AbstractExecuteLocalQueryView):
    def build_response(self, data_list):
        """Build the paginated list of data

        Args:
            data_list: List of data

        Returns:
            Paginated list of data
        """
        # get paginator
        paginator = StandardResultsSetPagination()
        # get requested page from list of results
        page = paginator.paginate_queryset(data_list, self.request)

        # FIXME: See if can use reverse to include data id, and avoid format
        # Get detail view base url (to be completed with data id)
        detail_url_base = reverse("core_main_app_data_detail")
        url_access_data = reverse("core_explore_common_app_get_result_from_data_id")
        url_permission_data = reverse("core_main_app_rest_data_permissions")

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

            detail_url = "{0}?id={1}".format(detail_url_base, str(data.id))

            # Use the PID link if the app is installed, and a PID is defined for the
            # document
            if "core_linked_records_app" in settings.INSTALLED_APPS:
                from core_linked_records_app.components.pid_settings import (
                    api as pid_settings_api,
                )
                from core_linked_records_app.components.data import api as data_api

                if pid_settings_api.get().auto_set_pid:
                    try:
                        pid_url = data_api.get_pid_for_data(data.id, self.request)
                        if pid_url is not None:  # Ensure the PID is set
                            detail_url = pid_url
                    except ApiError as exc:
                        # If there is an error with the PID, fallback to regular data
                        # url.
                        logger.warning(
                            f"An error occured while retrieving PID url: {str(exc)}"
                        )
                        pass

            results.append(
                Result(
                    title=data.title,
                    xml_content=data.xml_content,
                    template_info=template_info[template],
                    permission_url="{0}?ids={1}".format(
                        url_permission_data, f'%5B"{str(data.id)}"%5D'
                    ),
                    detail_url=detail_url,
                    access_data_url="{0}?id={1}".format(url_access_data, str(data.id)),
                    last_modification_date=pytz.utc.localize(
                        data.last_modification_date
                    ),
                )
            )

        # serialize results
        serialized_results = ResultSerializer(results, many=True)
        # return http response
        return paginator.get_paginated_response(serialized_results.data)
