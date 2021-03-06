from django.conf.urls import patterns, include, url
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.importlib import import_module


from . import apiviews
from . import models
from . import views


class Admin2(object):
    """
    The base Admin2 object.
    It keeps a registry of all registered Models and collects the urls of their
    related ModelAdmin2 instances.

    It also provides an index view that serves as an entry point to the admin site.
    """
    index_view = views.IndexView
    api_index_view = apiviews.IndexAPIView

    def __init__(self, name='admin2'):
        self.registry = {}
        self.apps = {}
        self.name = name

    def register(self, model, model_admin=None, **kwargs):
        """
        Registers the given model with the given admin class. Once a model is
        registered in self.registry, we also add it to app registries in
        self.apps.

        If no model_admin is passed, it will use ModelAdmin2. If keyword
        arguments are given they will be passed to the admin class on
        instantiation.

        If a model is already registered, this will raise ImproperlyConfigured.


        """
        if model in self.registry:
            raise ImproperlyConfigured('%s is already registered in django-admin2' % model)
        if not model_admin:
            model_admin = models.ModelAdmin2
        self.registry[model] = model_admin(model, admin=self, **kwargs)

        # Add the model to the apps registry
        app_label = model._meta.app_label
        if app_label in self.apps.keys():
            self.apps[app_label][model] = self.registry[model]
        else:
            self.apps[app_label] = {model: self.registry[model]}

    def deregister(self, model):
        """
        Deregisters the given model. Remove the model from the self.app as well

        If the model is not already registered, this will raise ImproperlyConfigured.
        """
        try:
            del self.registry[model]
        except KeyError:
            raise ImproperlyConfigured('%s was never registered in django-admin2' % model)

        # Remove the model from the apps registry
        # Get the app label
        app_label = model._meta.app_label
        # Delete the model from it's app registry
        del self.apps[app_label][model]

        # if no more models in an app's registry
        # then delete the app from the apps.
        if self.apps[app_label] is {}:
            del self.apps[app_label]  # no

    def autodiscover(self):
        """
        Autodiscovers all admin2.py modules for apps in INSTALLED_APPS by
        trying to import them.
        """
        apps = []
        for app_name in [x for x in settings.INSTALLED_APPS]:
            try:
                import_module("%s.admin2" % app_name)
            except ImportError as e:
                if str(e) == "No module named admin2":
                    continue
                raise e

    def get_index_kwargs(self):
        return {
            'registry': self.registry,
            'apps': self.apps,
        }

    def get_api_index_kwargs(self):
        return {
            'registry': self.registry,
            'apps': self.apps,
        }

    def get_urls(self):
        urlpatterns = patterns('',
            url(r'^$', self.index_view.as_view(**self.get_index_kwargs()), name='dashboard'),
            url(r'^api/v0/$',
            self.api_index_view.as_view(**self.get_api_index_kwargs()), name='api-index'),
        )
        for model, model_admin in self.registry.iteritems():
            urlpatterns += patterns('',
                url('^{}/{}/'.format(
                    model._meta.app_label,
                    model._meta.object_name.lower()),
                    include(model_admin.urls)),
                url('^api/v0/{}/{}/'.format(
                    model._meta.app_label,
                    model._meta.object_name.lower()),
                    include(model_admin.api_urls)),
            )
        return urlpatterns

    @property
    def urls(self):
        # We set the application and instance namespace here
        return self.get_urls(), self.name, self.name
