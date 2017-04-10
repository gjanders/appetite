"""Example of filter functions

String values from templated files and objects are passed through this function.  Values can be manipulated and passed
back to be used as jinja2 templated values.
"""


class FilterFunctions(object):
    def test_filtering(self, contents): # pylint: disable=no-self-use
        """Function to test filtering for unit testing"""

        if contents == "test_filter":
            return "text_has_been_filtered"

        return contents
