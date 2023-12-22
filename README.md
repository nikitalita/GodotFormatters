# README #

I use Xcode and LLDB to debug my Qt programs, and got tired with there being no visualisation for all the built-in types. Here I endeavour to make all of these types visible through the debugger. Works with Qt 5.x.

# Installation #

Clone this repo somewhere, e.g. ~/qtlldb. Then add the following lines to your ~/.lldbinit:

```
command script import ~/qtlldb/GodotFormatters.py
command source ~/qtlldb/GodotFormatters.lldb
```
