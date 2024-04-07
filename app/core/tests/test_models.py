from django.test import TestCase
from django.contrib.auth import get_user_model
from decimal import Decimal
from core import models


def create_user():
    """ Create test user """
    return get_user_model().objects.create_user(
        email='test@example.com',
        password='testpassword123'
    )


class ModelTest(TestCase):

    def test_create_user_with_email_successful(self):
        """Creating user with email is successful"""

        email = 'test@example.com'
        password = 'testpass111'
        user = get_user_model().objects.create_user(email=email,
                                                    password=password)
        self.assertEqual(user.email, email)
        self.assertTrue(user.check_password(password))

    def test_new_user_email_normalized(self):
        """ Test email normalized """
        sample_emails = [
            ['test1@EXAMPLE.com', 'test1@example.com'],
            ['Test2@Example.com', 'Test2@example.com'],
            ['TEST3@EXAMPLE.com', 'TEST3@example.com'],
            ['test4@example.COM', 'test4@example.com'],
        ]
        for email, expected in sample_emails:
            user = get_user_model().objects.create_user(email, 'sample123')
            self.assertEqual(user.email, expected)

    def test_new_user_without_email_raises_error(self):
        """ Test creating user without email raises error """
        with self.assertRaises(ValueError):
            get_user_model().objects.create_user('', 'test123')

    def test_create_superuser(self):
        """ Test creating superuser """
        user = get_user_model().objects.create_superuser(
            "test@example.com",
            "test123"
        )

        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)

    def test_create_recipe(self):
        """ Test creating new recipe """
        user = create_user()
        recipe = models.Recipe.objects.create(
            user=user,
            title='Sample recipe name',
            time_minutes=5,
            price=Decimal('5.50'),
            description='Sample recipe description'
        )

        self.assertEqual(str(recipe), recipe.title)

    def test_create_tag(self):
        user = create_user()
        tag = models.Tag.objects.create(
            name='Sample tag',
            user=user
        )
        self.assertEqual(str(tag), tag.name)

    def test_create_ingredient(self):
        """ Test creating an ingredient is successful """
        user = create_user()
        ingredient = models.Ingredient.objects.create(
            user=user,
            name='Ingredient1'
        )

        self.assertEqual(str(ingredient), ingredient.name)
