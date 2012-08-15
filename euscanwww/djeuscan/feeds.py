import json

from django.contrib.syndication.views import Feed, FeedDoesNotExist
from django.shortcuts import get_object_or_404
from django.utils.feedgenerator import Atom1Feed
from django.core.urlresolvers import reverse
from django.db.models import Q

from euscan.version import gentoo_unstable

from djeuscan.models import Package, Herd, Maintainer, VersionLog
from djeuscan.helpers import get_profile, get_account_versionlogs


class BaseFeed(Feed):
    feed_type = Atom1Feed
    author_name = 'euscan'
    item_author_name = author_name
    ttl = 3600

    def item_title(self, vlog):
        return str(vlog)

    def item_description(self, vlog):
        if vlog.overlay:
            txt = 'Version %s-%s [%s] of package %s ' % \
                (vlog.version, vlog.revision, vlog.slot, vlog.package)
        else:
            txt = 'Version %s of package %s ' % (vlog.version, vlog.package)
        if vlog.action == vlog.VERSION_REMOVED:
            if not vlog.overlay:
                txt += 'has been removed upstream'
            else:
                txt += 'has been removed from overlay "%s"' % vlog.overlay
        if vlog.action == vlog.VERSION_ADDED:
            if not vlog.overlay:
                txt += 'has been added upstream'
            else:
                txt += 'has been added to overlay "%s"' % vlog.overlay

        return txt

    def item_link(self, vlog):
        kwargs = {'category': vlog.package.category,
                  'package': vlog.package.name}
        return "%s#version-%s-%s:%s-%s" % (
            reverse('djeuscan.views.package', kwargs=kwargs),
            vlog.version, vlog.revision, vlog.slot, vlog.overlay,
        )

    def item_pubdate(self, vlog):
        return vlog.datetime

    def item_categories(self, vlog):
        return [vlog.package.category]

    def items(self, data=None):
        user = data.get("user", None) if data else None
        options = data.get("options", {}) if data else {}

        # first of all consider options, then user preferences
        try:
            upstream_info = json.loads(options.get("upstream_info", "1"))
            portage_info = json.loads(options.get("portage_info", "1"))
            show_adds = json.loads(options.get("show_adds", "1"))
            show_removals = json.loads(options.get("show_removals", "1"))
            ignore_pre = json.loads(options.get("ignore_pre", "0"))
            ignore_pre_if_stable = json.loads(
                options.get("ignore_pre_if_stable", "0")
            )
        except ValueError:
            return []

        if user and not options:
            profile = get_profile(user)
            upstream_info = profile.feed_upstream_info
            portage_info = profile.feed_portage_info
            show_adds = profile.feed_show_adds
            show_removals = profile.feed_show_removals
            ignore_pre = profile.feed_ignore_pre
            ignore_pre_if_stable = profile.feed_ignore_pre_if_stable

        ret, max_items = self._items(data)

        if not upstream_info:
            ret = ret.exclude(overlay="")
        if not portage_info:
            ret = ret.exclude(~Q(overlay=""))
        if not show_adds:
            ret = ret.exclude(action=VersionLog.VERSION_ADDED)
        if not show_removals:
            ret = ret.exclude(action=VersionLog.VERSION_REMOVED)
        if ignore_pre:
            ret = ret.exclude(vtype__in=gentoo_unstable)
        if ignore_pre_if_stable:
            ret = ret.exclude(
                ~Q(package__last_version_gentoo__vtype__in=gentoo_unstable),
                vtype__in=gentoo_unstable
            )

        return ret.order_by("-datetime")[:max_items]


class GlobalFeed(BaseFeed):
    title = "euscan"
    link = "/"
    description = "Last euscan changes"

    def get_object(self, request):
        return {"options": request.GET}

    def categories(self, data):
        categories = Package.objects.categories()
        return [category['category'] for category in categories]

    def _items(self, data):
        return VersionLog.objects.all(), 250


class PackageFeed(BaseFeed):
    feed_type = Atom1Feed

    def get_object(self, request, category, package):
        return {
            "obj": get_object_or_404(Package, category=category, name=package),
            "options": request.GET,
        }

    def title(self, data):
        return "%s" % data["obj"]

    def link(self, data):
        return reverse('djeuscan.views.package', args=[data["obj"].category,
                       data["obj"].name])

    def description(self, data):
        return data["obj"].description

    def _items(self, data):
        return VersionLog.objects.for_package(data["obj"]), 30

    def item_description(self, vlog):
        return ''


class MaintainerFeed(BaseFeed):
    feed_type = Atom1Feed

    def get_object(self, request, maintainer_id):
        return {
            "obj": get_object_or_404(Maintainer, id=maintainer_id),
            "options": request.GET,
        }

    def title(self, data):
        return "%s" % data["obj"]

    def description(self, data):
        return "Last changes for %s" % data["obj"]

    def link(self, data):
        return reverse('djeuscan.views.maintainer',
                       kwargs={'maintainer_id': data["obj"].id})

    def _items(self, data):
        return VersionLog.objects.for_maintainer(data["obj"]), 50


class HerdFeed(BaseFeed):
    feed_type = Atom1Feed

    def get_object(self, request, herd):
        return {
            "obj": get_object_or_404(Herd, herd=herd),
            "options": request.GET,
        }

    def title(self, data):
        return "%s" % data["obj"]

    def description(self, data):
        return "Last changes for %s" % data["obj"]

    def link(self, data):
        return reverse('djeuscan.views.herd',
                       kwargs={'herd': data["obj"].herd})

    def _items(self, data):
        return VersionLog.objects.for_herd(data["obj"]), 100


class CategoryFeed(BaseFeed):
    feed_type = Atom1Feed

    def get_object(self, request, category):
        if not Package.objects.categories().count():
            raise FeedDoesNotExist
        return {
            "obj": category,
            "options": request.GET,
        }

    def title(self, data):
        return "%s" % data["obj"]

    def description(self, data):
        return "Last changes for %s" % data["obj"]

    def link(self, data):
        return reverse('djeuscan.views.category', args=[data["obj"]])

    def _items(self, data):
        return VersionLog.objects.for_category(data["obj"]), 100


class UserFeed(BaseFeed):
    link = "/"

    def description(self, data):
        return "%s - last euscan changes" % data["user"]

    def title(self, data):
        return "%s - watched packages" % data["user"]

    def get_object(self, request):
        return {
            "user": request.user,
            "options": request.GET,
        }

    def _items(self, data):
        user, options = data["user"], data["options"]

        profile = get_profile(user)
        vlogs = get_account_versionlogs(profile)

        return vlogs, 100
