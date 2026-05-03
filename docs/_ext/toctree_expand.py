"""
Sphinx extension to add :expand: option to toctree directive.

Usage in RST files:
    .. toctree::
       :hidden:
       :expand:
       
       page1
       page2

This will mark the toctree to be expanded by default in the sidebar.
"""

from docutils import nodes
from sphinx.directives.other import TocTree
from sphinx.application import Sphinx


def setup(app: Sphinx):
    """Setup the extension."""
    
    # Add 'expand' option to toctree directive
    TocTree.option_spec['expand'] = lambda x: True
    
    # Connect to doctree-resolved event to add metadata
    app.connect('doctree-resolved', process_toctree_expand)
    
    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }


def process_toctree_expand(app, doctree, docname):
    """
    Process toctree nodes and add expand metadata.
    
    This adds a custom attribute to toctree nodes that have the :expand: option.
    The attribute will be used by JavaScript to expand the section in the sidebar.
    """
    for node in doctree.traverse(nodes.compound):
        # Check if this is a toctree node
        if 'toctree-wrapper' in node.get('classes', []):
            # Find the actual toctree node
            for toctree_node in node.traverse():
                if hasattr(toctree_node, 'attributes') and 'expand' in toctree_node.attributes:
                    # Mark this toctree for expansion
                    # We'll store this in the document metadata
                    if not hasattr(app.env, 'toctree_expand_pages'):
                        app.env.toctree_expand_pages = set()
                    app.env.toctree_expand_pages.add(docname)
