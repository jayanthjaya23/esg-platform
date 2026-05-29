"""
User models with organization-level isolation.

Custom user model extends Django's AbstractUser to add organization
context and role-based access control.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom user model with organization context.
    
    Users always belong to exactly one organization.
    Organization membership is immutable after initial assignment.
    """
    
    ROLE_CHOICES = [
        ('analyst', 'Data Analyst'),
        ('reviewer', 'ESG Reviewer'),
        ('admin', 'Organization Admin'),
    ]
    
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='users',
        help_text="Organization this user belongs to"
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='analyst',
        help_text="User role determines permissions"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When user was created"
    )
    
    class Meta:
        db_table = 'users_user'
        unique_together = [['organization', 'email']]
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.email} ({self.organization.name})"
    
    def has_role(self, role):
        """Check if user has a specific role."""
        return self.role == role
    
    def is_reviewer(self):
        """Check if user can approve records."""
        return self.role in ['reviewer', 'admin']
    
    def is_admin(self):
        """Check if user is organization admin."""
        return self.role == 'admin'