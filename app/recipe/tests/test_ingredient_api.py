"""
Test for the ingredients API
"""

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Ingredient

from recipe.serializers import IngredientSerializer

INGREDIENTS_URL = reverse('recipe:ingredient-list')


def create_user(email='test@example.com', password='testpass123'):
    return get_user_model().objects.create_user(email, password)


def detail_url(ingredient_id: str):
    return reverse('recipe:ingredient-detail', args=[ingredient_id])


class PublicIngredientsApiTests(TestCase):
    """ Test unauthenticated API requests """

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(INGREDIENTS_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateIngredientsApiTests(TestCase):
    """ Test authenticated API requests """

    def setUp(self):
        self.client = APIClient()
        self.user = create_user()
        self.client.force_authenticate(self.user)

    def test_retrieve_ingredients(self):
        Ingredient.objects.create(name='Test1', user=self.user)
        Ingredient.objects.create(name='Test2', user=self.user)

        res = self.client.get(INGREDIENTS_URL)

        ingredients = Ingredient.objects.all().order_by('-name')
        serializer = IngredientSerializer(ingredients, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_ingredients_limited_to_authenticated_user(self):
        user2 = create_user(email='user2@example.com')
        Ingredient.objects.create(user=user2, name='Salt')
        ingredient = Ingredient.objects.create(user=self.user, name='Banana')

        res = self.client.get(INGREDIENTS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['name'], ingredient.name)
        self.assertEqual(res.data[0]['id'], ingredient.id)

    def test_update_ingredient(self):
        """ Test updating an ingredient """
        ingredient = Ingredient.objects.create(user=self.user, name='Cilantro')
        payload = {
            'name': 'Coriander'
        }
        url = detail_url(ingredient.id)
        res = self.client.patch(url, payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ingredient.refresh_from_db()
        self.assertEqual(ingredient.name, payload['name'])

    def test_delete_ingredient(self):
        ingredient = Ingredient.objects.create(user=self.user, name='Lettuce')
        url = detail_url(ingredient.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Ingredient.objects.filter(user=self.user).exists())
