from docutils import nodes
from docutils.parsers.rst import Directive


class _BaseAliasAdmonition(Directive):
    has_content = True
    optional_arguments = 1
    final_argument_whitespace = True
    default_title = ""

    def run(self):
        title_text = self.arguments[0] if self.arguments else self.default_title
        admonition = nodes.admonition()
        admonition += nodes.title(text=title_text)
        self.state.nested_parse(self.content, self.content_offset, admonition)
        return [admonition]


class SuccessAdmonition(_BaseAliasAdmonition):
    default_title = "Success"


class CriticalAdmonition(_BaseAliasAdmonition):
    default_title = "Critical"


def setup(app):
    app.add_directive("success", SuccessAdmonition)
    app.add_directive("critical", CriticalAdmonition)
    return {"version": "1.0", "parallel_read_safe": True}
