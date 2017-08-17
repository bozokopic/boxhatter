import sphinx_rtd_theme


extensions = ['sphinx.ext.imgmath',
              'sphinx.ext.graphviz',
              'sphinx.ext.todo']

project = 'Hatter'
version = '0.0.1'
master_doc = 'index'

html_theme = 'sphinx_rtd_theme'
html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]
html_use_index = False
html_show_sourcelink = False
html_show_sphinx = False
html_sidebars = {
   '**': ['globaltoc.html', 'relations.html']}

todo_include_todos = True
