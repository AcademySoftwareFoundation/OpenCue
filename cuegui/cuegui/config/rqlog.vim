" ===================
" Syntax highlighting:
" ===================

" This will override it if you have one: ~/.config/.cuetopia/rqlog.vim

" Syntax documentation:
" http://vimdoc.sourceforge.net/htmldoc/syntax.html#syntax

highlight Notice       term=bold ctermfg=Blue        guifg=Blue
highlight Warning      term=bold ctermfg=Magenta     guifg=Purple
highlight Error        term=bold ctermfg=red         guifg=white         gui=bold

"highlight NotUsed1    term=bold ctermfg=DarkCyan    guifg=DarkCyan
"highlight NotUsed2    term=bold ctermfg=Brown       guifg=Brown         gui=bold
"highlight NotUsed3    term=bold ctermfg=DarkGreen   guifg=SeaGreen      gui=bold
"highlight NotUsed4    term=bold ctermfg=DarkBlue    guifg=SlateBlue     gui=underline

syntax keyword  Purple      WARNING Warning warning
syntax keyword  Error       Aborting ERROR Error error failed
syntax match    Error       "Rendering Error"
syntax match    Error       "glibc detected"
syntax keyword  Notice      CUE_THREADS logDestination
syntax match    Notice      "RenderQ Job Complete"

