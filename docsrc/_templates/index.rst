Blocks
=============

This page list the classes gather in components directory. Except from
*base_component*, all the other classes implements one VHDL entity or a set of
them.

.. toctree::
   :titlesonly:

   {% for page in pages %}
   {% if page.top_level_object and page.display %}
   {{ page.include_path }}
   {% endif %}
   {% endfor %}
