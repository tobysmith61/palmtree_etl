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
        html = f'''
            <div id="hot_container_{name}" style="width:100%;height:300px;"></div>
            <p id="debug_{name}" style="color:red;">[EC2 Debug] Widget HTML rendered</p>
            <script>
                console.log("[EC2 Debug] Inline script loaded for {name}");
            </script>
        '''
        return mark_safe(html)

