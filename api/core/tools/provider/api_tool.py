from typing import Any, Dict, List, Union
from json import dumps

from core.model_runtime.entities.message_entities import PromptMessage
from core.tools.entities.tool_bundle import ApiBasedToolBundle
from core.tools.entities.tool_entities import AssistantAppMessage
from core.tools.provider.tool import Tool
from core.tools.errors import ToolProviderCredentialValidationError

import httpx
import requests

class ApiTool(Tool):
    api_bundle: ApiBasedToolBundle
    
    """
    Api tool
    """

    def validate_credentials(self, credentails: Dict[str, Any], parameters: Dict[str, Any]) -> None:
        """
            validate the credentials for Api tool
        """
        headers = {}

        if 'auth_type' not in credentails:
            raise ToolProviderCredentialValidationError('Missing auth_type')

        if credentails['auth_type'] == 'api_key':
            api_key_header = 'api_key'

            if 'api_key_header' in credentails:
                api_key_header = credentails['api_key_header']
            
            if 'api_key_value' not in credentails:
                raise ToolProviderCredentialValidationError('Missing api_key_value')
            
            headers[api_key_header] = credentails['api_key_value']

        needed_parameters = [parameter for parameter in self.api_bundle.parameters if parameter.required]
        for parameter in needed_parameters:
            if parameter.required and parameter.name not in parameters:
                raise ToolProviderCredentialValidationError(f"Missing required parameter {parameter.name}")
            
            if parameter.default is not None and parameter.name not in parameters:
                parameters[parameter.name] = parameter.default

        response = self.do_http_request(self.api_bundle.server_url, self.api_bundle.method, headers, parameters)
        # validate response
        self.validate_response(response)

    def validate_response(self, response: httpx.Response) -> None:
        """
            validate the response
        """
        pass
    
    def do_http_request(self, url: str, method: str, headers: Dict[str, Any], parameters: Dict[str, Any]) -> httpx.Response:
        """
            do http request depending on api bundle
        """
        method = method.lower()

        params = {}
        path_params = {}
        body = {}
        cookies = {}
        request_content_type = ''

        # check parameters
        for parameter in self.api_bundle.openapi['parameters']:
            if parameter['in'] == 'path':
                value = ''
                if parameter['name'] in parameters:
                    value = parameters[parameter['name']]
                elif parameter['required']:
                    raise ToolProviderCredentialValidationError(f"Missing required parameter {parameter['name']}")
                path_params[parameter['name']] = value

            elif parameter['in'] == 'query':
                value = ''
                if parameter['name'] in parameters:
                    value = parameters[parameter['name']]
                elif parameter['required']:
                    raise ToolProviderCredentialValidationError(f"Missing required parameter {parameter['name']}")
                params[parameter['name']] = value

            elif parameter['in'] == 'cookie':
                value = ''
                if parameter['name'] in parameters:
                    value = parameters[parameter['name']]
                elif parameter['required']:
                    raise ToolProviderCredentialValidationError(f"Missing required parameter {parameter['name']}")
                cookies[parameter['name']] = value

            elif parameter['in'] == 'header':
                value = ''
                if parameter['name'] in parameters:
                    value = parameters[parameter['name']]
                elif parameter['required']:
                    raise ToolProviderCredentialValidationError(f"Missing required parameter {parameter['name']}")
                headers[parameter['name']] = value

        # check if there is a request body and handle it
        if 'requestBody' in self.api_bundle.openapi and self.api_bundle.openapi['requestBody'] is not None:
            # handle json request body
            if 'content' in self.api_bundle.openapi['requestBody']:
                for content_type in self.api_bundle.openapi['requestBody']['content']:
                    headers['Content-Type'] = content_type
                    body_schema = self.api_bundle.openapi['requestBody']['content'][content_type]['schema']
                    required = body_schema['required'] if 'required' in body_schema else []
                    properties = body_schema['properties'] if 'properties' in body_schema else {}
                    for name, property in properties.items():
                        if name in parameters:
                            body[name] = parameters[name]
                        elif name in required:
                            raise ToolProviderCredentialValidationError(
                                f"Missing required parameter {name} in operation {self.api_bundle.operation_id}"
                            )
                        elif 'default' in property:
                            body[name] = property['default']
                        else:
                            body[name] = None
                    break
        
        # replace path parameters
        for name, value in path_params.items():
            url = url.replace(f'{{{name}}}', value)

        # parse http body data if needed, for GET/HEAD/OPTIONS/TRACE, the body is ignored
        if 'Content-Type' in headers:
            if headers['Content-Type'] == 'application/json':
                body = dumps(body)
            else:
                body = body
        
        # do http request
        if method == 'get':
            response = httpx.get(url, params=params, headers=headers, cookies=cookies, timeout=10)
        elif method == 'post':
            response = httpx.post(url, params=params, headers=headers, cookies=cookies, data=body, timeout=10)
        elif method == 'put':
            response = httpx.put(url, params=params, headers=headers, cookies=cookies, data=body, timeout=10)
        elif method == 'delete':
            """
            request body data is unsupported for DELETE method in standard http protocol
            however, OpenAPI 3.0 supports request body data for DELETE method, so we support it here by using requests
            """
            response = requests.delete(url, params=params, headers=headers, cookies=cookies, data=body, timeout=10)
        elif method == 'patch':
            response = httpx.patch(url, params=params, headers=headers, cookies=cookies, data=body, timeout=10)
        elif method == 'head':
            response = httpx.head(url, params=params, headers=headers, cookies=cookies, timeout=10)
        elif method == 'options':
            response = httpx.options(url, params=params, headers=headers, cookies=cookies, timeout=10)
        elif method == 'trace':
            response = httpx.trace(url, params=params, headers=headers, cookies=cookies, timeout=10)
        else:
            raise ValueError(f'Invalid http method {method}')
        
        return response

    def _invoke(self, tool_paramters: Dict[str, Any], credentials: Dict[str, Any], prompt_messages: List[PromptMessage]) \
        -> AssistantAppMessage | List[AssistantAppMessage]:
        pass