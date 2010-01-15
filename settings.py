import os
import site

site.addsitedir(os.path.join(os.path.dirname(__file__), 'lib', 'python'))

template_path = os.path.join(os.path.dirname(__file__), "templates/")
