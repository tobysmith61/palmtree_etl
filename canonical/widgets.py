from django import forms
from django.utils.safestring import mark_safe
import json

class ExcelWidget(forms.Widget):
    def __init__(self, readonly=False, attrs=None):
        super().__init__(attrs)
        self.readonly = readonly

    class Media:
        css = {
            'all':  (
                'https://cdn.jsdelivr.net/npm/handsontable@12.1.1/dist/handsontable.min.css',
                    )
        }
        js = (
            'https://cdn.jsdelivr.net/npm/handsontable@12.1.1/dist/handsontable.min.js',
        )

    def render(self, name, value, attrs=None, renderer=None):
        if not value:
            value = [["Column 1", "Column 2"], ["", ""]]
        elif isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                value = [["Column 1", "Column 2"], ["", ""]]

        hidden_value = json.dumps(value)
        read_only_js = "readOnly: true," if self.readonly else ""

        # Unique variable names using the field name
        html = f'''
        <div id="hot_container_{name}" style="width: 100%; margin-bottom: 10px;"></div>
        <input type="hidden" name="{name}" id="id_{name}" value='{hidden_value}'>
        <script>
            (function() {{
                const container_{name} = document.getElementById("hot_container_{name}");
                const input_{name} = document.getElementById("id_{name}");
                const hot_{name} = new Handsontable(container_{name}, {{
                    data: {hidden_value},
                    rowHeaders: true,
                    colHeaders: false,
                    {read_only_js}
                    contextMenu: true,
                    manualColumnResize: true,
                    manualRowResize: true,
                    minSpareRows: 0,
                    minSpareCols: 0,
                    stretchH: 'none',
                    autoRowSize: true,
                    height: 'auto',
                    licenseKey: "non-commercial-and-evaluation",
                    afterChange: function(changes, source) {{
                        if(!{str(self.readonly).lower()} && source !== 'loadData') {{
                            input_{name}.value = JSON.stringify(hot_{name}.getData());
                        }}
                    }},
                    afterRenderer: function(TD, row, col, prop, value, cellProperties) {{
                        if(row === 0) {{
                            TD.style.background = '#f0f0f0';
                            TD.style.fontWeight = 'bold';
                            TD.style.fontSize = '90%';
                        }}
                    }}
                }});

                // Force initial value to hidden input
                input_{name}.value = JSON.stringify(hot_{name}.getData());

                // Delay initial render slightly to avoid sizing issues
                setTimeout(() => hot_{name}.render(), 100);
            }})();
        </script>
        '''
        return mark_safe(html)
