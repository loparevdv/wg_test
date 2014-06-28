from django.conf.urls import patterns, include, url
import debug_toolbar
from django.contrib import admin

from django.views.generic import ListView
from swiss.models import Player

admin.autodiscover()

urlpatterns = patterns('',
	(r'^accounts/login/$', 'django.contrib.auth.views.login'),
	(r'^accounts/logout/$', 'django.contrib.auth.views.logout'),
	
    url(r'^swiss/', include('swiss.urls')),

    url(r'^admin/', include(admin.site.urls)),
    url(r'^__debug__/', include(debug_toolbar.urls)),

    url(r'$', ListView.as_view(model=Player)),
	url(r'/$', ListView.as_view(model=Player)),
)
