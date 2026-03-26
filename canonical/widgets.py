from django import forms
from django.utils.safestring import mark_safe
import json
from django.conf import settings

class PalmtreeExcelWidget(forms.Widget):
    def __init__(self, readonly=False, attrs=None):
        super().__init__(attrs)
        # Always readonly unless it's a staging server
        self.readonly = not getattr(settings, "IS_STAGING_SERVER", False)

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
        # Ensure value is a 2D array
        try:
            if isinstance(value, str):
                value = json.loads(value)
            elif value is None:
                value = []
        except Exception:
            value = []

        if not value:
            value = [["Column 1", "Column 2"], ["", ""]]

        hidden_value = json.dumps(value)
        read_only_js = "readOnly: true," if self.readonly else ""

        html = f'''
        <div>
            <button type="button" id="toggle_{name}" style="margin-bottom:10px;">Switch to JSON</button>
        </div>
        <div id="hot_container_{name}" style="width: 100%; height: 300px; margin-bottom: 10px;"></div>
        <textarea id="json_container_{name}" style="width:100%; height:300px; display:none;">{hidden_value}</textarea>
        <input type="hidden" name="{name}" id="id_{name}" value='{hidden_value}'>
        <script>
            (function() {{
                const container = document.getElementById("hot_container_{name}");
                const jsonContainer = document.getElementById("json_container_{name}");
                const input = document.getElementById("id_{name}");
                let isJsonView = false;

                function initHandsontable() {{
                    if (!container) return;
                    const hot = new Handsontable(container, {{
                        data: {hidden_value},
                        rowHeaders: true,
                        colHeaders: false,
                        {read_only_js}
                        contextMenu: true,
                        manualColumnResize: true,
                        manualRowResize: true,
                        minSpareRows: 1,
                        minSpareCols: 1,
                        stretchH: 'none',
                        autoRowSize: true,
                        height: 300,
                        licenseKey: "non-commercial-and-evaluation",
                        afterChange: function(changes, source) {{
                            if(!{str(self.readonly).lower()} && source !== 'loadData') {{
                                const data = hot.getData();
                                input.value = JSON.stringify(data);
                                jsonContainer.value = JSON.stringify(data, null, 2);
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
                    input.value = JSON.stringify(hot.getData());
                    setTimeout(() => hot.render(), 200);
                    return hot;
                }}

                const hotInstance = initHandsontable();

                // Keep hidden input updated when editing JSON directly
                jsonContainer.addEventListener("input", function() {{
                    input.value = jsonContainer.value;
                }});

                // Toggle button
                document.getElementById("toggle_{name}").addEventListener("click", function() {{
                    if(isJsonView) {{
                        // Switch to table
                        container.style.display = "block";
                        jsonContainer.style.display = "none";
                        try {{
                            const data = JSON.parse(jsonContainer.value);
                            hotInstance.loadData(data);
                            input.value = jsonContainer.value;
                        }} catch(e) {{
                            alert("Invalid JSON!");
                        }}
                        this.textContent = "Switch to JSON";
                        isJsonView = false;
                    }} else {{
                        // Switch to JSON
                        container.style.display = "none";
                        jsonContainer.style.display = "block";
                        jsonContainer.value = JSON.stringify(hotInstance.getData(), null, 2);
                        input.value = jsonContainer.value;
                        this.textContent = "Switch to Table";
                        isJsonView = true;
                    }}
                }});
            }})();
        </script>
        '''
        return mark_safe(html)