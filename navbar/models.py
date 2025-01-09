from django.db import models
from organization.models import Organization


# Create your models here.

class NavBar(models.Model):
    name = models.CharField(max_length=300)
    link = models.TextField()

    def __str__(self):
        return self.name


class SubNavBar(models.Model):
    navbar = models.ForeignKey(NavBar, on_delete=models.CASCADE)
    name = models.CharField(max_length=300)
    display_name = models.CharField(max_length=300,blank=True,null=True)
    link = models.TextField()

    def __str__(self):
        return self.name


class OrganizationParentNavBar(models.Model):
    navbar = models.ForeignKey(NavBar, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    enable = models.BooleanField(default=True)
    display_name = models.CharField(max_length=300)

    def __str__(self):
        return f"{self.organization} - {self.navbar.name}"


class OrganizationSubNavBar(models.Model):
    subnavbar = models.ForeignKey(SubNavBar, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    enable = models.BooleanField(default=True)
    navbar = models.ForeignKey(NavBar, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.organization} - {self.subnavbar.name}"
