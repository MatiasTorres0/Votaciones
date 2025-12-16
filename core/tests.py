#!/usr/bin/env python
"""
Unit tests for URL resolution and survey deletion functionality
"""

from django.test import TestCase, Client
from django.urls import reverse, resolve
from django.contrib.auth.models import User
from django.urls.exceptions import Resolver404
from core.models import Encuesta


class SurveyDeletionURLTests(TestCase):
    """Test suite for survey deletion URL resolution and functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.encuesta = Encuesta.objects.create(
            titulo='Test Survey',
            descripcion='Test Description'
        )
    
    def test_eliminar_encuesta_url_resolution(self):
        """Test that the eliminar_encuesta URL resolves correctly"""
        # Test URL reversal
        url = reverse('eliminar_encuesta', kwargs={'encuesta_id': self.encuesta.id})
        self.assertEqual(url, f'/eliminar_encuesta/{self.encuesta.id}/')
        
        # Test URL resolution
        resolver = resolve(f'/eliminar_encuesta/{self.encuesta.id}/')
        self.assertEqual(resolver.view_name, 'eliminar_encuesta')
        self.assertEqual(resolver.func.__name__, 'eliminar_encuesta')
    
    def test_wrong_url_pattern_fails(self):
        """Test that incorrect URL patterns fail to resolve"""
        with self.assertRaises(Resolver404):
            resolve('/encuestas/eliminar/10/')
    
    def test_eliminar_encuesta_requires_login(self):
        """Test that survey deletion requires authentication"""
        response = self.client.get(f'/eliminar_encuesta/{self.encuesta.id}/')
        # Should redirect to login since user is not authenticated
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)
    
    def test_eliminar_encuesta_with_authentication(self):
        """Test survey deletion with authenticated user"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(f'/eliminar_encuesta/{self.encuesta.id}/')
        # Should redirect after successful deletion
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/lista_encuestas/')
    
    def test_eliminar_encuesta_with_invalid_id(self):
        """Test survey deletion with non-existent ID"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get('/eliminar_encuesta/99999/')
        # Should return 404 for non-existent survey
        self.assertEqual(response.status_code, 404)


class SurveyURLPatternTests(TestCase):
    """Test suite for all survey-related URL patterns"""
    
    def test_all_survey_url_patterns(self):
        """Test that all survey-related URL patterns work correctly"""
        patterns_to_test = [
            ('lista_encuestas', {}, '/lista_encuestas/'),
            ('crear_encuesta', {}, '/crear_encuesta/'),
            ('editar_encuesta', {'encuesta_id': 1}, '/editar_encuesta/1/'),
            ('eliminar_encuesta', {'encuesta_id': 1}, '/eliminar_encuesta/1/'),
        ]
        
        for pattern_name, kwargs, expected_url in patterns_to_test:
            with self.subTest(pattern=pattern_name):
                # Test URL reversal
                url = reverse(pattern_name, kwargs=kwargs)
                self.assertEqual(url, expected_url)
                
                # Test URL resolution (except for delete which requires auth)
                if pattern_name != 'eliminar_encuesta':
                    resolver = resolve(expected_url)
                    self.assertEqual(resolver.view_name, pattern_name)


# Additional test to verify the fix
class JavaScriptURLFixTests(TestCase):
    """Test to verify the JavaScript URL fix"""
    
    def test_javascript_url_correction(self):
        """Verify that the JavaScript code now uses the correct URL pattern"""
        # Read the template file to check the JavaScript code
        with open('core/templates/listar/lista_encuestas.html', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check that the old incorrect URL pattern is not present
        self.assertNotIn('/encuestas/eliminar/', content)
        
        # Check that the new correct URL pattern is present
        self.assertIn('/eliminar_encuesta/', content)