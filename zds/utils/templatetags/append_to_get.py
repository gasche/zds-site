from django import template
from functools import wraps

register = template.Library()

"""
Decorator to facilitate template tag creation.
"""


def easy_tag(func):
    """
    Deal with the repetitive parts of parsing template tags :

     - Wraps functions attributes;
     - Raise `TemplateSyntaxError` if arguments are not well formated.

    :rtype: function
    :param func: Function to wraps.
    :type func: function
    """

    @wraps(func)
    def inner(_, token):
        splitted_arg = token.split_contents()
        try:
            return func(*splitted_arg)
        except TypeError:
            import inspect
            args = inspect.getargspec(func).args[1:]

            err_msg = 'Bad arguments for tag "{0}".\nThe tag "{0}" take {1} arguments ({2}).\n {3} were provided ({4}).'
            fstring = err_msg.format(splitted_arg[0],
                                     len(args),
                                     ", ".join(args),
                                     len(splitted_arg),
                                     ", ".join(splitted_arg))
            raise template.TemplateSyntaxError(fstring)
    return inner


class AppendGetNode(template.Node):
    """
    Template node allowing to render an URL appending argument to current GET address.

    Parse a string like `key1=var1,key2=var2` and generate a new URL with the provided parameters appended to current
    parameters.
    """

    def __init__(self, arg_list):
        """
        Create a template node which append `arg_list` to GET URL.

        :param str arg_list: the argument list to append.
        """

        self.__dict_pairs = {}
        for pair in arg_list.split(','):
            try:
                key, val = pair.split('=')
                self.__dict_pairs[key] = template.Variable(val)
            except ValueError:
                raise template.TemplateSyntaxError(
                    "Bad argument format. '{}' must use the format 'key1=var1,key2=var2'".format(arg_list))

    def render(self, context):
        """
        Render the new URL according to the current context.

        :param context: Current context.
        :return: New URL with arguments appended.
        :rtype: str
        """
        get = context['request'].GET.copy()
        path = context['request'].META['PATH_INFO']

        for key in self.__dict_pairs:
            get[key] = self.__dict_pairs[key].resolve(context)

        if len(get) > 0:
            list_arg = [u"{0}={1}".format(key, value) for key in get.keys() for value in get.getlist(key)]
            path += u"?" + u"&".join(list_arg)

        return path


@register.tag()
@easy_tag
def append_to_get(_, arg_list):
    """Render an URL appending argument to current GET address.

    :param _: Tag name (not used)
    :param arg_list: Argument list like `key1=var1,key2=var2`
    :return: Template node.
    """
    return AppendGetNode(arg_list)
