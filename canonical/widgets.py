from django import forms
from django.utils.safestring import mark_safe
import json
from django.conf import settings


class PalmtreeExcelWidget(forms.Widget):
    def __init__(self, readonly=False, attrs=None):
        super().__init__(attrs)
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
            <button type="button" id="toggle_{name}" style="margin-bottom:10px;">JSON</button>
        </div>

        <div id="hot_container_{name}" style="width: 100%; height: 300px; margin-bottom: 10px;"></div>

        <textarea id="json_container_{name}" style="width:100%; height:300px; display:none;"></textarea>

        <input type="hidden" name="{name}" id="id_{name}" value='{hidden_value}'>

        <script>
        (function() {{
            const container = document.getElementById("hot_container_{name}");
            const jsonContainer = document.getElementById("json_container_{name}");
            const input = document.getElementById("id_{name}");
            let isJsonView = false;

            function formatCompact(data) {{
                return "[\\n" + data.map(row => "  " + JSON.stringify(row)).join(",\\n") + "\\n]";
            }}

            function initHandsontable() {{
                const initialData = JSON.parse(input.value || "[]");

                const hot = new Handsontable(container, {{
                    data: initialData,
                    rowHeaders: true,
                    colHeaders: false,
                    {read_only_js}
                    contextMenu: true,
                    manualColumnResize: true,
                    manualRowResize: true,
                    minSpareRows: 1,
                    minSpareCols: 1,
                    stretchH: 'none',
                    autoRowSize: false,
                    height: 300,
                    licenseKey: "non-commercial-and-evaluation",

                    afterChange: function(changes, source) {{
                        if (!{str(self.readonly).lower()} && source !== 'loadData') {{
                            const data = hot.getData();
                            input.value = JSON.stringify(data); // ALWAYS clean
                            jsonContainer.value = formatCompact(data);
                        }}
                    }},

                    afterRenderer: function(TD, row) {{
                        if(row === 0) {{
                            TD.style.background = '#f0f0f0';
                            TD.style.fontWeight = 'bold';
                            TD.style.fontSize = '90%';
                        }}
                    }}
                }});

                // initial sync
                const data = hot.getData();
                input.value = JSON.stringify(data);
                jsonContainer.value = formatCompact(data);

                setTimeout(() => hot.render(), 200);

                return hot;
            }}

            const hotInstance = initHandsontable();

            // JSON editor → hidden input (SAFE)
            jsonContainer.addEventListener("input", function() {{
                try {{
                    const parsed = JSON.parse(jsonContainer.value);
                    input.value = JSON.stringify(parsed); // normalize only
                }} catch(e) {{
                    // ignore invalid JSON (don't corrupt form)
                }}
            }});

            // Toggle
            document.getElementById("toggle_{name}").addEventListener("click", function() {{
                if (isJsonView) {{
                    // JSON → TABLE
                    try {{
                        const parsed = JSON.parse(jsonContainer.value);
                        hotInstance.loadData(parsed);
                        input.value = JSON.stringify(parsed);
                    }} catch(e) {{
                        alert("Invalid JSON!");
                        return;
                    }}

                    container.style.display = "block";
                    jsonContainer.style.display = "none";
                    this.textContent = "JSON";
                    isJsonView = false;

                }} else {{
                    // TABLE → JSON
                    const data = hotInstance.getData();
                    jsonContainer.value = formatCompact(data);
                    input.value = JSON.stringify(data);

                    container.style.display = "none";
                    jsonContainer.style.display = "block";
                    this.textContent = "Table";
                    isJsonView = true;
                }}
            }});

        }})();
        </script>
        '''
        return mark_safe(html)