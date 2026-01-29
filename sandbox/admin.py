from django.contrib import admin
from mptt.admin import DraggableMPTTAdmin
from .models import Group


@admin.register(Group)
class GroupAdmin(DraggableMPTTAdmin):
    mptt_indent_field = "name"
    list_display = ("tree_actions", "indented_title")
    list_display_links = ("indented_title",)


# use these later

# group = Group.objects.get(name="Engineering")
# group.get_children()
# group.get_descendants()
# group.get_ancestors()