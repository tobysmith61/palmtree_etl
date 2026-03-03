from django import forms
from django.utils.safestring import mark_safe
import json

class ExcelWidget(forms.Widget):
    def __init__(self, readonly=False, attrs=None):
        super().__init__(attrs)
        self.readonly = readonly

    class Media:
        css = {
            'all': (
                'https://cdn.jsdelivr.net/npm/handsontable@12.1.1/dist/handsontable.min.css',
            )
        }
        js = (
            'https://cdn.jsdelivr.net/npm/handsontable@12.1.1/dist/handsontable.min.js',
        )

    def render(self, name, value, attrs=None, renderer=None):
        return mark_safe(f'''
            <div id="hot_container_{name}"></div>
            <p style="color:red;">[Debug] Widget rendered for {name}</p>
            <script>console.log("Inline script loaded for {name}")</script>
        ''')