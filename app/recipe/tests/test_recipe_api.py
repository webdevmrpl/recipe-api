"""
Test for recipe APIs
"""

from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Recipe, Tag, Ingredient
from recipe.serializers import RecipeSerializer, RecipeDetailSerializer

import tempfile
import os

from PIL import Image

RECIPES_URL = reverse('recipe:recipe-list')


def detail_url(recipe_id):
    """ Create and return recipe detail URL """
    return reverse('recipe:recipe-detail', args=[recipe_id])


def image_upload_url(recipe_id):
    """ Create and return image upload URL """
    return reverse("recipe:recipe-upload-image", args=[recipe_id])


def create_recipe(user, **params):
    """ Create and return sample recipe """
    defaults = {
        'title': 'Sample recipe title',
        'time_minutes': 22,
        'price': Decimal('5.25'),
        'description': 'Sample description',
        'link': 'http://example.com/recipe.pdf'
    }

    defaults.update(params)
    recipe = Recipe.objects.create(user=user, **defaults)
    return recipe


def create_user(**params):
    """ Create and return new user """
    return get_user_model().objects.create_user(**params)


class PublicRecipeAPITest(TestCase):
    """ Test unauthenticated API requests """

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """ Test auth is required to access API """
        res = self.client.get(RECIPES_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateRecipeAPITest(TestCase):
    """ Test authenticated API requests """

    def setUp(self):
        self.client = APIClient()
        self.user = create_user(email='user@example.com',
                                password='testpass123', )
        self.client.force_authenticate(self.user)

    def test_retrieve_recipes(self):
        """ Test retrieving a list of recipes """

        create_recipe(user=self.user)
        create_recipe(user=self.user)

        res = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.all().order_by('-id')
        serializer = RecipeSerializer(recipes, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_recipe_limited_to_user(self):
        """ Test list of recipes is limited to authenticated user """

        other_user = create_user(
            email='other@example.com',
            password='othertestpassword123'
        )
        create_recipe(user=other_user)
        create_recipe(user=self.user)

        res = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.filter(user=self.user)
        serializer = RecipeSerializer(recipes, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_get_recipe_detail(self):
        """ Test get recipe detail """
        recipe = create_recipe(user=self.user)

        url = detail_url(recipe.id)
        res = self.client.get(url)
        serializer = RecipeDetailSerializer(recipe)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_recipe(self):
        """ Test creating new recipe """

        paylod = {
            'title': 'Sample recipe',
            'time_minutes': 30,
            'price': Decimal('5.99')
        }

        res = self.client.post(RECIPES_URL, paylod)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=res.data['id'])
        for k, v in paylod.items():
            self.assertEqual(getattr(recipe, k), v)
        self.assertEqual(recipe.user, self.user)

    def test_partial_update(self):
        """ Test partial update of a recipe """
        original_link = "https://example.com/recipe.pdf"
        recipe = create_recipe(
            user=self.user,
            title='Sample title',
            link=original_link,
        )

        payload = {
            'title': 'New recipe title'
        }

        url = detail_url(recipe.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        self.assertEqual(recipe.title, payload['title'])
        self.assertEqual(recipe.link, original_link)
        self.assertEqual(recipe.user, self.user)

    def test_full_update(self):
        recipe = create_recipe(
            user=self.user,
            title='Sample recipe',
            link='https://example.com/recipe.pdf',
            description='Sample recipe description',
        )
        payload = {
            'title': 'New recipe title',
            'link': 'https://example.com./new_recipe.pdf',
            'description': 'New recipe description',
            'time_minutes': 20,
            'price': Decimal('12.5')
        }
        url = detail_url(recipe.id)
        res = self.client.put(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        for k, v in payload.items():
            self.assertEqual(getattr(recipe, k), v)
        self.assertEqual(recipe.user, self.user)

    def test_update_user_returns_error(self):
        """ Test changing the recipe results in an error """
        recipe = create_recipe(
            user=self.user,
            title='Sample recipe',
            link='https://example.com/recipe.pdf',
            description='Sample recipe description',
        )
        new_user = create_user(
            email='newuser@example.com',
            password='testpassword123'
        )
        url = detail_url(recipe.id)
        payload = {
            'user': new_user
        }

        res = self.client.patch(url, payload)  # noqa
        recipe.refresh_from_db()
        self.assertEqual(recipe.user, self.user)

    def test_delete_recipe(self):
        """ Test deleting recipe successful """
        recipe = create_recipe(
            user=self.user,
            title='Sample recipe',
            link='https://example.com/recipe.pdf',
            description='Sample recipe description',
        )
        url = detail_url(recipe.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Recipe.objects.filter(id=recipe.id).exists())

    def test_delete_other_users_recipe_error(self):
        """ Test trying to delete another users recipe result in an error """
        new_user = create_user(email='sample11@example.com',
                               password='newpassword123')
        recipe = create_recipe(user=new_user)
        url = detail_url(recipe.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Recipe.objects.filter(id=recipe.id).exists())

    def test_create_recipe_with_new_tag(self):
        """ Testing creating recipe with new tags """
        payload = {
            'title': 'Thai Prawn Curry',
            'time_minutes': 30,
            'price': Decimal('30.0'),
            'tags': [{'name': 'Thai'}, {'name': 'Dinner'}]
        }

        res = self.client.post(RECIPES_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)
        for tag in payload['tags']:
            exists = recipe.tags.filter(
                name=tag['name'],
                user=self.user
            ).exists()
            self.assertTrue(exists)

    def test_create_recipe_with_existing_tags(self):
        """ Test creating recipe with existing tag """
        tag_indian = Tag.objects.create(name='Indian', user=self.user)
        payload = {
            'title': 'Pongal',
            'time_minutes': 60,
            "price": Decimal('4.50'),
            'tags': [{'name': 'Indian'}, {'name': 'Breakfast'}]
        }

        res = self.client.post(RECIPES_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)
        self.assertIn(tag_indian, recipe.tags.all())
        for tag in payload['tags']:
            exists = recipe.tags.filter(
                name=tag['name'],
                user=self.user
            ).exists()
            self.assertTrue(exists)

    def test_create_tag_on_update(self):
        """ Test creating tag when updating a recipe """
        recipe = create_recipe(user=self.user)

        payload = {'tags': [{'name': 'Lunch'}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        new_tag = Tag.objects.get(user=self.user, name='Lunch')
        self.assertIn(new_tag, recipe.tags.all())

    def test_update_recipe_assign_tag(self):
        tag_breakfast = Tag.objects.create(user=self.user, name='Breakfast')
        recipe = create_recipe(user=self.user)
        recipe.tags.add(tag_breakfast)

        tag_lunch = Tag.objects.create(user=self.user, name='Lunch')
        payload = {
            'tags': [{'name': 'Lunch'}]
        }

        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(tag_lunch, recipe.tags.all())
        self.assertNotIn(tag_breakfast, recipe.tags.all())

    def test_clear_recipe_tags(self):
        """ Test clearing recipes' tags """
        tag = Tag.objects.create(user=self.user, name='Dessert')
        recipe = create_recipe(user=self.user)
        recipe.tags.add(tag)

        payload = {
            'tags': []
        }

        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.tags.count(), 0)

    def test_create_recipe_with_new_ingredients(self):
        """ Test creating a recipe with new ingredients """
        payload = {
            'title': 'Cauliflower Tacos',
            'time_minutes': 60,
            'price': Decimal('4.30'),
            'ingredients': [
                {'name': 'Cauliflower'}, {'name': 'Salt'}
            ]
        }
        res = self.client.post(RECIPES_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.ingredients.count(), 2)

        for ingredient in payload['ingredients']:
            exists = recipe.ingredients.filter(
                name=ingredient['name'],
                user=self.user
            ).exists()
            self.assertTrue(exists)

    def test_create_recipe_with_existing_ingredient(self):
        """ Test creating a recipe with new ingredients """
        ingredient = Ingredient.objects.create(user=self.user, name='Salt')
        payload = {
            'title': 'Cauliflower Tacos',
            'time_minutes': 60,
            'price': Decimal('4.30'),
            'ingredients': [
                {'name': 'Cauliflower'}, {'name': 'Salt'}
            ]
        }

        res = self.client.post(RECIPES_URL, payload, format='json')
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.ingredients.count(), 2)
        self.assertIn(ingredient, recipe.ingredients.all())

        for ingredient in payload['ingredients']:
            exists = recipe.ingredients.filter(
                user=self.user,
                name=ingredient['name']).exists()
            self.assertTrue(exists)

    def test_create_ingredient_on_update(self):
        """ Test creating an ingredient when updating recipe """

        recipe = create_recipe(user=self.user)

        payload = {
            'ingredients': [{'name': 'Limes'}]
        }

        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        self.assertEqual(recipe.ingredients.count(), 1)
        ingredient = Ingredient.objects.get(user=self.user, name='Limes')
        self.assertIn(ingredient, recipe.ingredients.all())

    def test_recipe_assign_ingredient(self):
        """ Test assigning an existing ingredient when updating recipe """
        ingredient1 = Ingredient.objects.create(user=self.user, name='Pepper')
        recipe = create_recipe(user=self.user)
        recipe.ingredients.add(ingredient1)

        ingredient2 = Ingredient.objects.create(user=self.user, name='Salt')
        payload = {
            'ingredients': [{'name': 'Salt'}]
        }

        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')
        recipe.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(ingredient2, recipe.ingredients.all())
        self.assertNotIn(ingredient1, recipe.ingredients.all())

    def test_clear_ingredients(self):
        """ Test clearing ingredients """

        ingredient = Ingredient.objects.create(user=self.user, name='Pepper')
        recipe = create_recipe(user=self.user)
        recipe.ingredients.add(ingredient)

        payload = {'ingredients': []}

        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')
        recipe.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.ingredients.count(), 0)

    def test_filter_tags(self):
        """ Test filtering recipe by tags """
        r1 = create_recipe(user=self.user, title='Thai Vegetable Curry')
        r2 = create_recipe(user=self.user, title='Aubergine with Tahini')
        tag1 = Tag.objects.create(user=self.user, name='Vegan')
        tag2 = Tag.objects.create(user=self.user, name='Vegetarian')
        r1.tags.add(tag1)
        r2.tags.add(tag2)
        r3 = create_recipe(user=self.user, title='Fish and Chips')

        params = {'tags': f'{tag1.id},{tag2.id}'}
        res = self.client.get(RECIPES_URL, params)

        s1 = RecipeSerializer(r1)
        s2 = RecipeSerializer(r2)
        s3 = RecipeSerializer(r3)

        self.assertIn(s1.data, res.data)
        self.assertIn(s2.data, res.data)
        self.assertNotIn(s3.data, res.data)

    def test_filter_by_ingredients(self):
        """ Test filtering recipe by ingredients """
        r1 = create_recipe(user=self.user, title='Posh Beans on Toast')
        r2 = create_recipe(user=self.user, title='Chicken Cacciatore')
        in1 = Ingredient.objects.create(user=self.user, name='Feta Cheese')
        in2 = Ingredient.objects.create(user=self.user, name='Chicken')
        r1.ingredients.add(in1)
        r2.ingredients.add(in2)
        r3 = create_recipe(user=self.user, title='Red Lentil Daal')

        params = {'ingredients': f'{in1.id},{in2.id}'}
        res = self.client.get(RECIPES_URL, params)

        s1 = RecipeSerializer(r1)
        s2 = RecipeSerializer(r2)
        s3 = RecipeSerializer(r3)

        self.assertIn(s1.data, res.data)
        self.assertIn(s2.data, res.data)
        self.assertNotIn(s3.data, res.data)


class ImageUploadTests(TestCase):
    """ Test for image upload API """

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user('user@example.com', 'password123')
        self.client.force_authenticate(user=self.user)
        self.recipe = create_recipe(user=self.user)

    def tearDown(self):
        self.recipe.image.delete()

    def test_upload_image(self):
        url = image_upload_url(self.recipe.id)
        with tempfile.NamedTemporaryFile(suffix='.jpg') as image_file:
            img = Image.new('RGB', (10, 10))
            img.save(image_file, format='JPEG')
            image_file.seek(0)
            payload = {'image': image_file}
            res = self.client.post(url, payload, format='multipart')

        self.recipe.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('image', res.data)
        self.assertTrue(os.path.exists(self.recipe.image.path))

    def test_upload_image_bad_request(self):
        """ Test uploading invalid image """
        url = image_upload_url(self.recipe.id)
        payload = {'image': 'notanimage'}
        res = self.client.post(url, payload, format='multipart')

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
