from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from unittest.mock import patch

User = get_user_model()

class DockerAPITests(APITestCase):
    def setUp(self):
        # Create an admin user
        self.admin_user = User.objects.create_superuser(
            username='admin_test',
            email='admin_test@example.com',
            password='admin_password123'
        )
        # Create a regular user
        self.regular_user = User.objects.create_user(
            username='user_test',
            email='user_test@example.com',
            password='user_password123'
        )
        
        self.list_containers_url = reverse('docker-list-containers')
        # URL for GetDockerContainerPathsView (needs a placeholder container_id)
        self.container_paths_url_template = reverse('docker-container-paths', kwargs={'container_id': 'PLACEHOLDER_ID'})

    def test_list_docker_containers_permissions_and_basic_success(self):
        """
        Test permissions for the list_docker_containers endpoint and a basic success scenario.
        """
        # 1. Test unauthenticated access
        response = self.client.get(self.list_containers_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # 2. Test access with regular user (should be forbidden)
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get(self.list_containers_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.client.force_authenticate(user=None) # Clear authentication

        # 3. Test access with admin user (should be successful)
        # We mock the actual service call to avoid real Docker interaction
        mock_container_data = [
            {"id": "abc123xyz", "name": "test_container_1", "image": "test_image:latest", "status": "running"},
            {"id": "def456uvw", "name": "test_container_2", "image": "another_image:1.0", "status": "running"}
        ]
        
        with patch('core.views.list_running_containers') as mock_list_containers:
            mock_list_containers.return_value = mock_container_data
            
            self.client.force_authenticate(user=self.admin_user)
            response = self.client.get(self.list_containers_url)
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(len(response.data), 2)
            self.assertEqual(response.data[0]['name'], 'test_container_1')
            mock_list_containers.assert_called_once() # Ensure our service function was called

    def test_list_docker_containers_service_error(self):
        """
        Test the list_docker_containers endpoint when the service returns an error.
        """
        error_message = "Docker API error: Connection refused"
        with patch('core.views.list_running_containers') as mock_list_containers:
            mock_list_containers.return_value = error_message
            
            self.client.force_authenticate(user=self.admin_user)
            response = self.client.get(self.list_containers_url)
            
            self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
            self.assertIn('error', response.data)
            self.assertEqual(response.data['error'], error_message)
            mock_list_containers.assert_called_once()

    def test_get_container_paths_permissions_and_success(self):
        """
        Test permissions and basic success scenario for GetDockerContainerPathsView.
        """
        test_container_id = "test_container_123"
        specific_container_paths_url = self.container_paths_url_template.replace('PLACEHOLDER_ID', test_container_id)

        # 1. Test unauthenticated access
        response = self.client.get(specific_container_paths_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # 2. Test access with regular user (should be forbidden)
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get(specific_container_paths_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.client.force_authenticate(user=None)  # Clear authentication

        # 3. Test access with admin user (should be successful)
        mock_path_data = ['/mnt/code/project_a', '/var/www/html']
        with patch('core.views.get_container_code_paths') as mock_get_paths:
            mock_get_paths.return_value = mock_path_data
            
            self.client.force_authenticate(user=self.admin_user)
            response = self.client.get(specific_container_paths_url)
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(len(response.data), 2)
            self.assertEqual(response.data[0], '/mnt/code/project_a')
            # Ensure the service function was called with the correct container_id
            mock_get_paths.assert_called_once_with(test_container_id)

    def test_get_container_paths_not_found(self):
        """
        Test GetDockerContainerPathsView when the container is not found.
        """
        test_container_id = "non_existent_container"
        specific_container_paths_url = self.container_paths_url_template.replace('PLACEHOLDER_ID', test_container_id)
        error_message = f"Container '{test_container_id}' not found."

        with patch('core.views.get_container_code_paths') as mock_get_paths:
            mock_get_paths.return_value = error_message
            
            self.client.force_authenticate(user=self.admin_user)
            response = self.client.get(specific_container_paths_url)
            
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
            self.assertIn('error', response.data)
            self.assertEqual(response.data['error'], error_message)
            mock_get_paths.assert_called_once_with(test_container_id)

    def test_get_container_paths_service_error(self):
        """
        Test GetDockerContainerPathsView when the service returns a generic error.
        """
        test_container_id = "another_container_id"
        specific_container_paths_url = self.container_paths_url_template.replace('PLACEHOLDER_ID', test_container_id)
        error_message = "Docker API error: Unexpected issue"

        with patch('core.views.get_container_code_paths') as mock_get_paths:
            mock_get_paths.return_value = error_message
            
            self.client.force_authenticate(user=self.admin_user)
            response = self.client.get(specific_container_paths_url)
            
            self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
            self.assertIn('error', response.data)
            self.assertEqual(response.data['error'], error_message)
            mock_get_paths.assert_called_once_with(test_container_id)

    # Additional test methods for GetDockerContainerPathsView will be added here
    # and for error cases of ListDockerContainersView. 