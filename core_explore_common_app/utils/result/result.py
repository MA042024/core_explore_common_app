"""Explore Common result utils
"""
from core_main_app.components.version_manager import api as version_manager_api
from core_explore_common_app.components.result.models import Result
from core_explore_common_app.rest.result.serializers import ResultSerializer, ResultBaseSerializer
import json


def get_template_info(template, include_template_id=True):
    """Gets template information
    Args:
        template: Template to get information from.
        include_template_id: Include the template id in the information

    Returns:
        Template information.

    """
    version_manager = version_manager_api.get_from_version(template)
    version_number = version_manager_api.get_version_number(version_manager, template.id)

    # Here the id need to be set anyway because is expected by the serializer
    return_value = {'id': template.id if include_template_id else '',
                    'name': "{0} (Version {1})".format(version_manager.title, version_number),
                    'hash': template.hash}

    return return_value


def get_result_from_rest_data_response(response):
    """ Returns result object from data rest response

    Args:
        response:

    Returns:

    """
    # data serialization
    result_serialized = ResultBaseSerializer(data=json.loads(response.text))
    # Validate data
    result_serialized.is_valid(True)
    # Build a Result
    result = Result(title=result_serialized.data['title'],
                    xml_content=result_serialized.data['xml_content'])
    # Serialize results
    return_value = ResultSerializer(result)
    # Returns the response
    return return_value.data
