"""This module constructs the Bokeh document of interactive plots and widgets.

The code sets up 'roots' (layout objects) to be added to curdoc(), which can
then be turned into div and script elements by the bokeh server. These elements
are embedded in the accompanying Flask app.

Data are arranged in the following structures:

1) A dictionary of pandas dataframes.
- df: the full strains dataframe, built from imported Google Sheets data.
- current: the subset of df that remains after filtering (via plot selection)
- counts: a 'counts' dataframe with columns ['categ', 'val', 'n']. Provides
    the number of rows in df where column 'categ' has value 'val'.
- pairs_df: dataframe with columns ['categ', 'val']. Has one row for each
    value ('val') observed in each column ('categ').

2) Bokeh objects.
- p_counts: the interactive counts barplot.
- source_c: the data source (ColumnDataSource) underlying p_counts.
- source_c_orig: the pre-filtered data source for p_counts, for showing
    persistent gray bars that represent counts in the full strains data.
- data_table: the interactive, sortable table of (filtered) strains data.
- source_s: the ColumnDataSource holding data for data_table.
- button_refresh: a refresh button widget that will reload from Google Sheets.
- text_refresh: a text widget that shows data loading status.

"""
import os
from collections import OrderedDict
from dotenv import load_dotenv, find_dotenv

import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from bokeh.io import show
from bokeh.models import ColumnDataSource, HoverTool, FactorRange, Div, CustomJS
from bokeh.plotting import figure, curdoc
from bokeh.palettes import Spectral8
from bokeh.transform import factor_cmap
from bokeh.models.widgets import Button, DataTable, TableColumn, \
    HTMLTemplateFormatter
from bokeh.layouts import row, widgetbox, column


basedir = os.path.abspath(os.path.dirname(__file__))
env_path = os.getenv('ENV_NAME', find_dotenv())
load_dotenv(env_path)
CREDS_JSON = os.environ.get('CREDS_JSON')
FEATHER_PATH = os.environ.get('FEATHER_PATH') or 'df.feather'

bar_bg_dict = {'color': 'whitesmoke', 'nonselection_color': 'whitesmoke', 
               'alpha': 0.9, 'nonselection_alpha': 0.9}  # #1f77b4
# nonselection_dict = {
#     'fill_alpha': 0.5,
#     'fill_color': '#1f77b4',
#     'line_alpha': 0.1,
#     'line_color': '#1f77b4'}

# select_cols = ['marker1', 'marker2', 'strain', 'origin', 'origin2', 'lab', 'submitter']  # organism
LABS = ['Schepartz', 'Soll', 'Cate']  # TODO: remove hard-coded lab names
PLOT_COLS = ['marker1', 'strain', 'origin', 'lab', 'submitter']  # organism, origin2, marker2
LINK_COLS = 'benchling_url'
LAB_COL = 'lab'
FIG_WIDTH = 1200
FIG_HEIGHT = 350
cell_template = """<span href="#" data-toggle="tooltip" title="<%= value %>"><%= value %></span>"""
url_template = """<a href="<%= value %>" target="_blank"><%= value %></a>"""

col_dict = {
    'Name': 'submitter',
    'Description': 'desc',
    'Lab': 'lab',
    'Benchling File': 'benchling_url',
    'Entry #': 'entry',
    'Organism': 'organism',
    'Marker 1': 'marker1',
    'Marker 2': 'marker2',
    'Origin': 'origin',
    'Origin 2': 'origin2',
    'Plasmid': 'plasmid',
    'Promoter': 'promoter',
    'Strain': 'strain'
}
col_dict_r = {col_dict[i]: i for i in col_dict}

table_cols = OrderedDict([
    ('lab', {'width': 70}),
    ('entry', {'width': 38}),
    ('organism', {'width': 60}),
    ('strain', {'width': 80}),
    ('plasmid', {'width': 165}),
    ('marker1', {'width': 55}),
    ('marker2', {'width': 55}),
    ('origin', {'width': 55}),
    ('origin2', {'width': 45}),
    ('promoter', {'width': 60}),
    ('benchling_url', {'width': 90}),
    ('desc', {'width': 320}),
    ('submitter', {'width': 70})])


def get_gsheet_dict():
    """Get dictionary of sheet_name: sheet object."""
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        CREDS_JSON, scope)

    gc = gspread.authorize(credentials)
    # display('List spreadsheet files:', gc.list_spreadsheet_files())
    file = gc.open("C-GEM strains list")
    wsheets = file.worksheets()
    sheet_dict = OrderedDict([(i.title, i) for i in wsheets])
    return sheet_dict


def load_df(load_gsheet=False):
    """Load COMPLETE strains dataframe from Google Sheets or local file."""
    if os.path.exists(FEATHER_PATH) and not load_gsheet:
        df = pd.read_feather(FEATHER_PATH)
        df = df[[i for i in table_cols]]
        return df
    # labs = [i for i in sheet_dict if i != 'Introduction']
    sheet_dict = get_gsheet_dict()
    df_list = []
    # headers_lists = []
    for lab in LABS:
        sheet = sheet_dict[lab]
        vals = sheet.get_all_records()
        # headers_lists.append(sheet.row_values(1))
        # print('headers: %s' % headers)
        vals = [i for i in vals if set(i.values()) != {''}]  # remove empty rows
        temp_df = pd.DataFrame(vals, dtype=str)
        temp_df.insert(0, 'Lab', lab)
        df_list.append(temp_df)
    # GET FULL COLUMN SET (in case not exact duplicates)
    all_cols = []
    for temp_df in df_list:
        for header in temp_df.columns:
            if header not in all_cols:
                all_cols.append(header)
    # print('Columns: %s' % all_cols)
    df = pd.concat(df_list, axis=0, ignore_index=True, sort=False)[all_cols]
    df.rename(columns=col_dict, inplace=True)
    df = df[[i for i in table_cols]].copy()
    df = df.applymap(lambda v: '<blank>' if v == '' else v)
    df.to_feather(FEATHER_PATH)
    return df


def counts_from_strains(strains, pairs_df=None):
    """Get counts dataframe from strains table."""
    n_strains = len(strains)
    count_name = 'n'
    count_list = []
    for col in PLOT_COLS:
        if col == LAB_COL:
            vc = strains[col].value_counts().reindex(LABS, fill_value=0).sort_values(ascending=False)
        else:
            vc = strains[col].value_counts()
        # if (vc > 1).any() & (len(vc) < 10):
        vc.index.name = 'val'
        vc.name = 'n'
        if len(vc) > 1:
            s_all = pd.Series(name='n', 
                              index=pd.Index(name='val', data=['All']), 
                              data=[n_strains])
            vc = s_all.append(vc)
        vcd = vc.reset_index()
        vcd.insert(0, 'categ', col)
        count_list.append(vcd)
    counts = pd.concat(count_list, axis=0, ignore_index=True, sort=False)
    if pairs_df is not None:
        counts = pairs_df.merge(counts, how='left', on=['categ', 'val']).fillna(0)
    return counts


def update_data_dict(data_dict=None, strains=None, write_orig=False):
    data_dict['current'] = strains
    if write_orig:
        # Update all data
        data_dict['df'] = strains.copy()
        counts = counts_from_strains(strains)
        data_dict['counts'] = counts.copy()
        data_dict['pairs_df'] = counts[['categ', 'val']]
    else:
        # Update counts but don't overwrite pairs_df.
        counts = counts_from_strains(strains, pairs_df=data_dict['pairs_df'])
        data_dict['counts'] = counts.copy()
    return


def get_refresh_msg():
    """Get modification time message to accompany refresh button."""
    modtime = pd.datetime.utcfromtimestamp(os.path.getmtime(FEATHER_PATH))
    modtime_str = modtime.strftime('%Y-%m-%d %H:%M:%S')
    return 'Spreadsheet last loaded at {} UTC.'.format(modtime_str)


def initialize_counts_fig(counts):
    """Create bar plot from counts dataframe."""
    group = counts.groupby(['categ', 'val'])
    counts_x = [(i.categ, i.val) for ind, i in counts[['categ', 'val']].iterrows()]  # for xrange

    source_c = ColumnDataSource(group)
    source_c_orig = ColumnDataSource(group)  # will hold persistent original counts

    index_cmap = factor_cmap('categ_val', palette=Spectral8, factors=counts.categ.unique(), end=1)

    p = figure(plot_width=FIG_WIDTH, plot_height=FIG_HEIGHT, title="",
               x_range=FactorRange(*counts_x), toolbar_location=None, tools="tap",)

    p.vbar(x='categ_val', top='n_max', width=1, source=source_c_orig,
           **bar_bg_dict)
    bars_front = p.vbar(x='categ_val', top='n_max', width=1, source=source_c,
                        line_color="white", fill_color=index_cmap, )
    p.yaxis.axis_label = "Number of strains"
    p.yaxis.axis_label_text_font_size = "10pt"
    p.y_range.start = 0
    p.x_range.range_padding = 0.05
    p.xgrid.grid_line_color = None
    p.xaxis.axis_label = ""  # category
    p.xaxis.major_label_orientation = 1.2
    p.xaxis.major_label_text_font_size = "10pt"
    p.xaxis.group_text_font_size = "10pt"
    p.yaxis.major_label_text_font_size = "10pt"
    p.outline_line_color = None
    p.add_tools(HoverTool(tooltips=[("Count", "@n_max"), ("selector", "@categ_val")],
                          renderers=[bars_front]))
    return p, source_c, source_c_orig


df = load_df(load_gsheet=False)
data_dict = {}
update_data_dict(data_dict=data_dict, strains=df, write_orig=True)

source_s = ColumnDataSource(data=dict())  # strain data
p_counts, source_c, source_c_orig = initialize_counts_fig(data_dict['counts'])
columns = []  # FOR DataTable
for col in data_dict['df'].columns:
    if col in LINK_COLS:
        columns.append(TableColumn(field=col, title=col, 
            formatter=HTMLTemplateFormatter(template=url_template), **table_cols[col]))
    else:
        columns.append(TableColumn(field=col, title=col, 
            formatter=HTMLTemplateFormatter(template=cell_template), **table_cols[col]))
data_table = DataTable(source=source_s, columns=columns, width=FIG_WIDTH)
# DATA REFRESH WIDGETS
button_refresh = Button(label="Refresh data", button_type="warning")
text_refresh = Div(text=get_refresh_msg())


# UPDATES

def update_sources(data_dict, update_orig=False):
    """Update strains data source, infer+update counts source."""
    current = data_dict['current']
    new_dict = {col: list(current[col].replace('<blank>', ''))
                for col in current.columns}
    source_s.data = new_dict
    # UPDATE COUNTS LIST FROM NEW STRAIN LIST
    group = data_dict['counts'].groupby(['categ', 'val'])
    new_counts_dict = OrderedDict(ColumnDataSource(group).data)
    source_c.data = new_counts_dict
    if update_orig:
        counts_x = [(i.categ, i.val) for ind, i in data_dict['pairs_df'].iterrows()]
        p_counts.x_range.factors = counts_x
        source_c_orig.data = new_counts_dict.copy()


def refresh_data(data_dict):
    """Data refresh button response: fetch new data from gsheet, update page."""
    text_refresh.text = 'Loading...'
    df = load_df(load_gsheet=True)
    text_refresh.text = get_refresh_msg()
    update_data_dict(data_dict=data_dict, strains=df, write_orig=True)
    update_sources(data_dict, update_orig=True)


def plot_select(data_dict):
    # prog_list.append('called plot_select')
    inds = list(source_c.selected.indices)
    current = data_dict['df']  # full strains list, for filtering
    if inds:
        # FILTER DATA BASED ON SELECTED INDICES IN COUNTS PLOT
        # prog_list.append('no inds')
        s = source_c.data['categ_val'][inds]  # array of (categ, val) tuples
        categs, vals = zip(*s)
        sd = pd.DataFrame({'categ': categs, 'val': vals})
        sd = sd[sd.val != 'All']  # ignore 'All' selections.
        filter_dict = sd.groupby('categ')['val'].apply(set).to_dict()
        for categ in filter_dict:
            current = current[current[categ].isin(filter_dict[categ])]
        # prog_list.append(str(s))
        # text_div.text = '; '.join([str((categ, val)) for categ, val in s])
        # prog_list.append('updated text_div')
        for categ, val in s:
            if val == 'All':
                continue
            # prog_list.append((categ, val))
            current = current[current[categ] == val]
    update_data_dict(data_dict=data_dict, strains=current, write_orig=False)
    update_sources(data_dict)


source_c.selected.on_change('indices', lambda attr, old, new: plot_select(data_dict))
button_refresh.on_click(lambda: refresh_data(data_dict))
update_sources(data_dict)

source_s.selected.js_on_change('indices', CustomJS(
    args=dict(source=source_s, col_names=list(table_cols)), code="""
    temp_source = source;
    console.log(cb_obj);
    var inds = source.selected['1d']['indices'];
    if (inds.length == 1){
        /* update form with data from selected row */
        var use_ind = inds[0]
        var $form = document.getElementById('ship-form');
        var el_dict = $form.getElementsByTagName('input');
        for (var col_ind = 0; col_ind < col_names.length; col_ind++){
            var var_name = col_names[col_ind];
            el_dict[var_name].value = source.data[var_name][use_ind];
        }
        $form.submit()
    }
    else {
        console.log('Multiple rows selected: ' + inds);
    }
    """))

# LAYOUT
table = widgetbox(data_table)
table_row = row(table, sizing_mode="scale_width")  # (inputs, table)
refresh_row = row(button_refresh, text_refresh)
full = column(p_counts, table_row, refresh_row,
              sizing_mode="scale_width")  # widgetbox(text_div)


if __name__ != '__main__':
    # doc.add_root(full)
    curdoc().title = "Strains dashboard"
    curdoc().add_root(full)
    curdoc().template_variables["col_names"] = list(table_cols)

else:
    from bokeh.io import output_notebook
    output_notebook()

    def make_doc(doc):
        doc.add_root(full)
    nb = show(make_doc, notebook_handle=True)
