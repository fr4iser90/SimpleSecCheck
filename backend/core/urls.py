from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ProjectViewSet, ScanTargetViewSet, TargetGroupViewSet, 
    SecurityToolViewSet, ScanConfigurationViewSet, UserProfileViewSet,
    ApiKeyViewSet, ScanTriggerViewSet, ScanJobViewSet, 
    ProjectMembershipViewSet, UserViewSet, CIScanTriggerViewSet
)

router = DefaultRouter()
router.register(r'projects', ProjectViewSet, basename='project')
router.register(r'scan-targets', ScanTargetViewSet, basename='scantarget')
router.register(r'target-groups', TargetGroupViewSet, basename='targetgroup')
router.register(r'security-tools', SecurityToolViewSet, basename='securitytool')
router.register(r'scan-configurations', ScanConfigurationViewSet, basename='scanconfiguration')
router.register(r'profile', UserProfileViewSet, basename='userprofile')
router.register(r'api-keys', ApiKeyViewSet, basename='apikey')
router.register(r'scans', ScanTriggerViewSet, basename='scans')
router.register(r'scan-jobs', ScanJobViewSet, basename='scanjob')
router.register(r'project-memberships', ProjectMembershipViewSet, basename='projectmembership')
router.register(r'users', UserViewSet, basename='user')
router.register(r'ci/trigger-scan', CIScanTriggerViewSet, basename='ci-scan-trigger')

urlpatterns = [
    path('', include(router.urls)),
] 