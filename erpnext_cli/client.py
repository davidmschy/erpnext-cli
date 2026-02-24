"""
ERPNext/Frappe REST API client.
Provides both high-level SDK interface and low-level HTTP methods.
"""
from typing import Optional, Dict, Any, List, Union
import requests

from . import auth, config


class ERPNextError(Exception):
    """Exception raised for ERPNext API errors."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, response: Optional[Dict] = None):
        self.message = message
        self.status_code = status_code
        self.response = response
        super().__init__(self.message)
    
    def __str__(self):
        if self.status_code:
            return f"ERPNext API Error ({self.status_code}): {self.message}"
        return f"ERPNext API Error: {self.message}"


class ERPNextClient:
    """
    ERPNext/Frappe REST API client with OAuth2 authentication.
    
    Supports both OAuth2 and API key/secret authentication.
    Automatically handles token refresh and authentication headers.
    
    Example:
        # Using default site
        client = ERPNextClient()
        leads = client.list_docs('Lead', filters={'status': 'Open'})
        
        # Using specific site
        client = ERPNextClient(site_name='geniinow')
        doc = client.get_doc('Sales Order', 'SAL-ORD-2024-00001')
        
        # Override base URL and token (useful for testing)
        client = ERPNextClient(
            base_url='https://custom.erpnext.com',
            auth_token='token abc:xyz'
        )
    """
    
    def __init__(
        self,
        site_name: Optional[str] = None,
        base_url: Optional[str] = None,
        auth_token: Optional[str] = None
    ):
        """
        Initialize ERPNext client.
        
        Args:
            site_name: Site name from config. Uses default site if None.
            base_url: Override base URL (skips config lookup)
            auth_token: Override auth token (skips token refresh)
        """
        if base_url and auth_token:
            # Direct initialization with URL and token
            self.base_url = base_url.rstrip('/')
            self.site_name = site_name or 'custom'
            self._auth_token = auth_token
        else:
            # Load from config
            site_config = config.get_site(site_name)
            self.site_name = site_config['name']
            self.base_url = site_config['base_url']
            self._auth_token = None
        
        # Setup session
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
    
    def _get_auth_header(self) -> str:
        """Get valid authentication header value."""
        if self._auth_token:
            return self._auth_token
        
        # Get token from auth module (handles refresh automatically)
        token = auth.get_valid_token(self.site_name)
        
        # Check if it's already formatted (API key format)
        if token.startswith('token '):
            return token
        
        # OAuth2 Bearer token
        return f"Bearer {token}"
    
    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        json_data: Optional[Dict] = None
    ) -> Dict[Any, Any]:
        """
        Make HTTP request to ERPNext API.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (without base URL)
            params: Query parameters
            data: Form data
            json_data: JSON body data
            
        Returns:
            Response JSON data
            
        Raises:
            ERPNextError: On API error
        """
        # Ensure endpoint starts with /
        if not endpoint.startswith('/'):
            endpoint = '/' + endpoint
        
        url = f"{self.base_url}{endpoint}"
        
        # Set authorization header
        headers = {'Authorization': self._get_auth_header()}
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                data=data,
                json=json_data,
                headers=headers,
                timeout=30
            )
            
            # Parse response
            try:
                response_data = response.json()
            except ValueError:
                response_data = {'message': response.text}
            
            # Check for errors
            if not response.ok:
                error_message = self._extract_error_message(response_data)
                raise ERPNextError(
                    message=error_message,
                    status_code=response.status_code,
                    response=response_data
                )
            
            return response_data
        
        except requests.RequestException as e:
            raise ERPNextError(f"Request failed: {e}")
    
    def _extract_error_message(self, response_data: Dict) -> str:
        """Extract error message from response data."""
        if isinstance(response_data, dict):
            # Try common error message fields
            if 'message' in response_data:
                return response_data['message']
            if 'exception' in response_data:
                return response_data['exception']
            if 'exc' in response_data:
                return response_data['exc']
            if '_server_messages' in response_data:
                import json
                try:
                    messages = json.loads(response_data['_server_messages'])
                    if messages and isinstance(messages, list):
                        return json.loads(messages[0]).get('message', str(messages[0]))
                except:
                    pass
        
        return str(response_data)
    
    # Low-level HTTP methods
    
    def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[Any, Any]:
        """
        Make GET request.
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            
        Returns:
            Response data
        """
        return self._request('GET', endpoint, params=params)
    
    def post(self, endpoint: str, data: Optional[Dict] = None) -> Dict[Any, Any]:
        """
        Make POST request.
        
        Args:
            endpoint: API endpoint
            data: JSON data
            
        Returns:
            Response data
        """
        return self._request('POST', endpoint, json_data=data)
    
    def put(self, endpoint: str, data: Optional[Dict] = None) -> Dict[Any, Any]:
        """
        Make PUT request.
        
        Args:
            endpoint: API endpoint
            data: JSON data
            
        Returns:
            Response data
        """
        return self._request('PUT', endpoint, json_data=data)
    
    def delete(self, endpoint: str) -> Dict[Any, Any]:
        """
        Make DELETE request.
        
        Args:
            endpoint: API endpoint
            
        Returns:
            Response data
        """
        return self._request('DELETE', endpoint)
    
    # DocType CRUD operations
    
    def get_doc(self, doctype: str, name: str) -> Dict[str, Any]:
        """
        Get a document by doctype and name.
        
        Args:
            doctype: Document type (e.g., 'Lead', 'Sales Order')
            name: Document name/ID
            
        Returns:
            Document data
            
        Example:
            doc = client.get_doc('Lead', 'LEAD-2024-00001')
        """
        response = self.get(f"/api/resource/{doctype}/{name}")
        return response.get('data', response)
    
    def list_docs(
        self,
        doctype: str,
        fields: Optional[List[str]] = None,
        filters: Optional[Union[Dict, List]] = None,
        limit_start: int = 0,
        limit_page_length: int = 20,
        order_by: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List documents of a doctype.
        
        Args:
            doctype: Document type
            fields: List of fields to return (default: all)
            filters: Filters as dict or list of lists
            limit_start: Offset for pagination
            limit_page_length: Number of records to return
            order_by: Sort order (e.g., 'creation desc', 'modified asc')
            
        Returns:
            List of documents
            
        Example:
            leads = client.list_docs(
                'Lead',
                fields=['name', 'lead_name', 'status'],
                filters={'status': 'Open'},
                limit_page_length=10
            )
        """
        params = {
            'limit_start': limit_start,
            'limit_page_length': limit_page_length
        }
        
        if fields:
            # Frappe expects JSON string for fields parameter
            import json
            params['fields'] = json.dumps(fields)
        
        if filters:
            # Frappe expects JSON string for filters
            import json
            params['filters'] = json.dumps(filters)
        
        if order_by:
            params['order_by'] = order_by
        
        response = self.get(f"/api/resource/{doctype}", params=params)
        return response.get('data', response)
    
    def create_doc(self, doctype: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new document.
        
        Args:
            doctype: Document type
            data: Document data
            
        Returns:
            Created document data
            
        Example:
            lead = client.create_doc('Lead', {
                'lead_name': 'John Doe',
                'email_id': 'john@example.com',
                'status': 'Open'
            })
        """
        payload = {'doctype': doctype, **data}
        response = self.post(f"/api/resource/{doctype}", data=payload)
        return response.get('data', response)
    
    def update_doc(self, doctype: str, name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing document.
        
        Args:
            doctype: Document type
            name: Document name/ID
            data: Fields to update
            
        Returns:
            Updated document data
            
        Example:
            client.update_doc('Lead', 'LEAD-2024-00001', {
                'status': 'Converted',
                'notes': 'Follow up completed'
            })
        """
        response = self.put(f"/api/resource/{doctype}/{name}", data=data)
        return response.get('data', response)
    
    def delete_doc(self, doctype: str, name: str) -> Dict[str, Any]:
        """
        Delete a document.
        
        Args:
            doctype: Document type
            name: Document name/ID
            
        Returns:
            Response data
            
        Example:
            client.delete_doc('Lead', 'LEAD-2024-00001')
        """
        return self.delete(f"/api/resource/{doctype}/{name}")
    
    # Convenience aliases
    
    def get_list(self, doctype: str, **kwargs) -> List[Dict[str, Any]]:
        """
        Alias for list_docs() with cleaner syntax.
        
        Example:
            leads = client.get_list('Lead', filters={'status': 'Open'}, limit_page_length=5)
        """
        return self.list_docs(doctype, **kwargs)
    
    # Method calling
    
    def call(self, method: str, **kwargs) -> Any:
        """
        Call a Frappe/ERPNext server-side method.
        
        Args:
            method: Method name (e.g., 'frappe.auth.get_logged_user')
            **kwargs: Method arguments
            
        Returns:
            Method response
            
        Example:
            user = client.call('frappe.auth.get_logged_user')
            result = client.call('myapp.api.custom_method', param1='value')
        """
        response = self.post(f"/api/method/{method}", data=kwargs)
        
        # Frappe wraps method responses in 'message' key
        if isinstance(response, dict) and 'message' in response:
            return response['message']
        
        return response
    
    def get_logged_user(self) -> str:
        """
        Get the currently authenticated user.
        
        Returns:
            User email/ID
        """
        return self.call('frappe.auth.get_logged_user')
    
    def get_api_version(self) -> Dict[str, Any]:
        """
        Get Frappe/ERPNext version information.
        
        Returns:
            Version information
        """
        return self.call('frappe.utils.change_log.get_versions')
