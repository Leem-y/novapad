"""
ui/theme.py  -  NovaPad Multi-Theme System
68 themes: 38 dark, 30 light.
"""
from __future__ import annotations
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui     import QColor, QPalette


def _t(bg_app,bg_win,bg_tool,bg_tbar,bg_tact,bg_tinact,
       bg_ed,bg_stat,bg_menu,bg_hov,bg_prs,bg_inp,bg_btn,
       acc,acc_hov,fg1,fg2,fg_m,fg_tact,fg_tinact,
       brd,brd_inp,sb_bg,sb_hdl,sep,
       sel_bg,sel_fg,fm_bg,fm_fg,fc_bg,fc_fg,
       cur,gut_bg,gut_fg,gut_cur,dark=True):
    return dict(
        bg_app=bg_app,bg_window=bg_win,bg_toolbar=bg_tool,
        bg_tab_bar=bg_tbar,bg_tab_active=bg_tact,bg_tab_inactive=bg_tinact,
        bg_editor=bg_ed,bg_statusbar=bg_stat,bg_menu=bg_menu,
        bg_hover=bg_hov,bg_pressed=bg_prs,bg_input=bg_inp,bg_button=bg_btn,
        accent=acc,accent_hover=acc_hov,
        fg_primary=fg1,fg_secondary=fg2,fg_muted=fg_m,
        fg_tab_active=fg_tact,fg_tab_inactive=fg_tinact,
        border=brd,border_input=brd_inp,
        scrollbar_bg=sb_bg,scrollbar_handle=sb_hdl,separator=sep,
        sel_bg=sel_bg,sel_fg=sel_fg,
        find_match_bg=fm_bg,find_match_fg=fm_fg,
        find_cur_bg=fc_bg,find_cur_fg=fc_fg,
        cursor=cur,gutter_bg=gut_bg,gutter_fg=gut_fg,gutter_cur=gut_cur,
        is_dark=dark,
    )

THEMES = {
    # ── DARK (38) ────────────────────────────────────────────────────
    "NovaPad Dark":_t("#1C1C1E","#1C1C1E","#2C2C2E","#252528","#1C1C1E","#2C2C2E","#1E1E1E","#111113","#2C2C2E","#3A3A3C","#48484A","#2C2C2E","#3A3A3C","#0A84FF","#409CFF","#F2F2F7","#AEAEB2","#636366","#F2F2F7","#98989D","#3A3A3C","#48484A","#1C1C1E","#48484A","#38383A","#0A84FF","#FFFFFF","#513B00","#FFE066","#FF9500","#FFFFFF","#F2F2F7","#1C1F26","#4B5263","#ABB2BF"),
    "VS Code Dark+":_t("#1E1E1E","#1E1E1E","#252526","#2D2D2D","#1E1E1E","#2D2D2D","#1E1E1E","#007ACC","#252526","#2A2D2E","#3F3F46","#3C3C3C","#3C3C3C","#007ACC","#1C97EA","#D4D4D4","#9D9D9D","#5A5A5A","#FFFFFF","#969696","#3C3C3C","#474747","#1E1E1E","#424242","#3C3C3C","#264F78","#FFFFFF","#613315","#FFD700","#F1BD6C","#000000","#AEAFAD","#252526","#858585","#C6C6C6"),
    "One Dark Pro":_t("#282C34","#282C34","#21252B","#21252B","#282C34","#21252B","#282C34","#21252B","#21252B","#2C313C","#3E4452","#21252B","#2C313C","#61AFEF","#82BFEF","#ABB2BF","#828997","#4B5263","#ABB2BF","#5C6370","#3E4452","#4B5263","#282C34","#4B5263","#3E4452","#3E4452","#ABB2BF","#3B3B00","#E5C07B","#E06C75","#282C34","#ABB2BF","#21252B","#495162","#ABB2BF"),
    "Monokai":_t("#272822","#272822","#1E1F1C","#272822","#272822","#1E1F1C","#272822","#1E1F1C","#1E1F1C","#3E3D32","#49483E","#1E1F1C","#3E3D32","#F92672","#FA5C8B","#F8F8F2","#CFCFC2","#75715E","#F8F8F2","#75715E","#49483E","#75715E","#272822","#49483E","#3E3D32","#49483E","#F8F8F2","#5F4A12","#FFE566","#F92672","#F8F8F2","#F8F8F0","#1E1F1C","#90908A","#F8F8F2"),
    "Dracula":_t("#282A36","#282A36","#21222C","#191A21","#282A36","#191A21","#282A36","#191A21","#21222C","#44475A","#6272A4","#21222C","#44475A","#BD93F9","#D6ACFF","#F8F8F2","#6272A4","#44475A","#F8F8F2","#6272A4","#44475A","#6272A4","#282A36","#44475A","#44475A","#44475A","#F8F8F2","#3B2A4A","#E9C6FF","#FF79C6","#F8F8F2","#F8F8F2","#21222C","#6272A4","#F8F8F2"),
    "Tokyo Night":_t("#1A1B26","#1A1B26","#16161E","#16161E","#1A1B26","#16161E","#1A1B26","#101014","#16161E","#292E42","#3B4261","#16161E","#292E42","#7AA2F7","#89B4FA","#C0CAF5","#A9B1D6","#565F89","#C0CAF5","#565F89","#292E42","#3B4261","#1A1B26","#3B4261","#292E42","#3B4261","#C0CAF5","#2A2A5A","#BB9AF7","#F7768E","#1A1B26","#C0CAF5","#16161E","#3B4261","#7AA2F7"),
    "Tokyo Night Storm":_t("#24283B","#24283B","#1F2335","#1F2335","#24283B","#1F2335","#24283B","#1D1F2B","#1F2335","#2F3549","#3B4261","#1F2335","#2F3549","#7AA2F7","#89B4FA","#C0CAF5","#A9B1D6","#565F89","#C0CAF5","#565F89","#2F3549","#3B4261","#24283B","#3B4261","#2F3549","#3B4261","#C0CAF5","#2D2F5A","#BB9AF7","#F7768E","#24283B","#C0CAF5","#1F2335","#3B4261","#7AA2F7"),
    "Gruvbox Dark":_t("#282828","#282828","#1D2021","#282828","#282828","#1D2021","#282828","#1D2021","#1D2021","#3C3836","#504945","#1D2021","#3C3836","#D79921","#FABD2F","#EBDBB2","#D5C4A1","#665C54","#EBDBB2","#928374","#3C3836","#504945","#282828","#504945","#3C3836","#504945","#EBDBB2","#3B2A00","#FABD2F","#CC241D","#EBDBB2","#EBDBB2","#1D2021","#665C54","#D5C4A1"),
    "Nord":_t("#2E3440","#2E3440","#3B4252","#2E3440","#3B4252","#2E3440","#2E3440","#272C36","#3B4252","#434C5E","#4C566A","#3B4252","#434C5E","#88C0D0","#B3DCE8","#ECEFF4","#D8DEE9","#4C566A","#ECEFF4","#D8DEE9","#3B4252","#434C5E","#2E3440","#4C566A","#3B4252","#4C566A","#ECEFF4","#3B3060","#E5CFFF","#BF616A","#ECEFF4","#D8DEE9","#3B4252","#4C566A","#8FBCBB"),
    "Catppuccin Mocha":_t("#1E1E2E","#1E1E2E","#181825","#181825","#1E1E2E","#181825","#1E1E2E","#11111B","#181825","#313244","#45475A","#181825","#313244","#CBA6F7","#DDB8FF","#CDD6F4","#BAC2DE","#45475A","#CDD6F4","#BAC2DE","#313244","#45475A","#1E1E2E","#45475A","#313244","#45475A","#CDD6F4","#3D2B5A","#D8B4FE","#F38BA8","#1E1E2E","#CDD6F4","#181825","#585B70","#A6ADC8"),
    "Catppuccin Macchiato":_t("#24273A","#24273A","#1E2030","#1E2030","#24273A","#1E2030","#24273A","#181926","#1E2030","#363A4F","#494D64","#1E2030","#363A4F","#C6A0F6","#DAB4FF","#CAD3F5","#B8C0E0","#494D64","#CAD3F5","#B8C0E0","#363A4F","#494D64","#24273A","#494D64","#363A4F","#363A4F","#CAD3F5","#3A2A55","#D5B0FF","#ED8796","#24273A","#CAD3F5","#1E2030","#5B6078","#A5ADCB"),
    "Catppuccin Frappe":_t("#303446","#303446","#292C3C","#292C3C","#303446","#292C3C","#303446","#232634","#292C3C","#414559","#51576D","#292C3C","#414559","#CA9EE6","#DDB8FF","#C6D0F5","#B5BFE2","#51576D","#C6D0F5","#838BA7","#414559","#51576D","#303446","#51576D","#414559","#414559","#C6D0F5","#362055","#CA9EE6","#E78284","#303446","#C6D0F5","#292C3C","#626880","#99D1DB"),
    "Solarized Dark":_t("#002B36","#002B36","#073642","#002B36","#073642","#002B36","#002B36","#001F27","#073642","#073642","#0D4A5A","#073642","#073642","#268BD2","#5AAFFF","#839496","#657B83","#586E75","#93A1A1","#657B83","#073642","#586E75","#002B36","#586E75","#073642","#073642","#93A1A1","#1C3A42","#93A1A1","#CB4B16","#FDF6E3","#839496","#073642","#586E75","#93A1A1"),
    "Material Dark":_t("#212121","#212121","#1A1A1A","#1A1A1A","#212121","#1A1A1A","#212121","#161616","#1A1A1A","#303030","#424242","#1A1A1A","#303030","#80CBC4","#A5D6D2","#EEFFFF","#B0BEC5","#546E7A","#EEFFFF","#B0BEC5","#303030","#424242","#212121","#424242","#303030","#425B67","#EEFFFF","#1A3A30","#80CBC4","#F07178","#EEFFFF","#EEFFFF","#1A1A1A","#546E7A","#80CBC4"),
    "Palenight":_t("#292D3E","#292D3E","#1F2330","#1F2330","#292D3E","#1F2330","#292D3E","#1A1E2E","#1F2330","#333747","#434759","#1F2330","#333747","#82AAFF","#A8C8FF","#A6ACCD","#676E95","#3B3F51","#A6ACCD","#676E95","#333747","#3B3F51","#292D3E","#3B3F51","#333747","#3B3F51","#A6ACCD","#2A2060","#BB80FF","#F07178","#A6ACCD","#A6ACCD","#1F2330","#3B3F51","#82AAFF"),
    "Ayu Dark":_t("#0D1017","#0D1017","#0A0E14","#0A0E14","#0D1017","#0A0E14","#0D1017","#070A0E","#0A0E14","#131721","#1F2430","#0A0E14","#131721","#E6B450","#F0C060","#B3B1AD","#5C6773","#3D4752","#B3B1AD","#3D4752","#0F131A","#1D2433","#0D1017","#1D2433","#131721","#1D2433","#B3B1AD","#2A1E00","#E6B450","#FF3333","#B3B1AD","#B3B1AD","#0A0E14","#3D4752","#5C6773"),
    "Tomorrow Night":_t("#1D1F21","#1D1F21","#161719","#161719","#1D1F21","#161719","#1D1F21","#141516","#161719","#282A2E","#373B41","#161719","#282A2E","#81A2BE","#A8C4D8","#C5C8C6","#969896","#666860","#C5C8C6","#969896","#282A2E","#373B41","#1D1F21","#373B41","#282A2E","#373B41","#C5C8C6","#2A2000","#F0C674","#CC6666","#C5C8C6","#C5C8C6","#161719","#666860","#969896"),
    "Cobalt2":_t("#193549","#193549","#122738","#122738","#193549","#122738","#193549","#0D1F2D","#122738","#1E4162","#0E3A5A","#122738","#1E4162","#FFC600","#FFD740","#FFFFFF","#9EBFE8","#0088FF","#FFFFFF","#9EBFE8","#1E4162","#0E3A5A","#193549","#0E3A5A","#1E4162","#0E3A5A","#FFFFFF","#2A2200","#FFC600","#FF628C","#FFFFFF","#FFFFFF","#122738","#0088FF","#9EBFE8"),
    "Night Owl":_t("#011627","#011627","#01111D","#01111D","#011627","#01111D","#011627","#010E17","#01111D","#0B2942","#0E3A5C","#01111D","#0B2942","#82AAFF","#A8C4FF","#D6DEEB","#637777","#1B2B34","#D6DEEB","#637777","#0B2942","#1B2B34","#011627","#1B2B34","#0B2942","#1B2B34","#D6DEEB","#0A1A30","#82AAFF","#EF5350","#D6DEEB","#D6DEEB","#01111D","#1B2B34","#4B6479"),
    "SynthWave 84":_t("#262335","#262335","#1A1831","#1A1831","#262335","#1A1831","#262335","#1A1831","#1A1831","#34294F","#483D6B","#1A1831","#34294F","#F97E72","#FF9E8C","#FFFFFF","#B893CE","#495495","#FFFFFF","#8B80C0","#34294F","#483D6B","#262335","#483D6B","#34294F","#483D6B","#FFFFFF","#2A1040","#FF7EDB","#F97E72","#FFFFFF","#FFFFFF","#1A1831","#495495","#B893CE"),
    "Rose Pine":_t("#191724","#191724","#1F1D2E","#191724","#1F1D2E","#191724","#191724","#141220","#1F1D2E","#26233A","#403D52","#1F1D2E","#26233A","#C4A7E7","#D4BFFF","#E0DEF4","#908CAA","#6E6A86","#E0DEF4","#6E6A86","#26233A","#403D52","#191724","#403D52","#26233A","#403D52","#E0DEF4","#2A1F40","#C4A7E7","#EB6F92","#E0DEF4","#E0DEF4","#1F1D2E","#6E6A86","#908CAA"),
    "Rose Pine Moon":_t("#232136","#232136","#2A273F","#232136","#2A273F","#232136","#232136","#1C1A2B","#2A273F","#393552","#44415A","#2A273F","#393552","#C4A7E7","#D4BFFF","#E0DEF4","#908CAA","#6E6A86","#E0DEF4","#6E6A86","#393552","#44415A","#232136","#44415A","#393552","#44415A","#E0DEF4","#2E2355","#C4A7E7","#EB6F92","#E0DEF4","#E0DEF4","#2A273F","#6E6A86","#908CAA"),
    "Kanagawa Wave":_t("#1F1F28","#1F1F28","#16161D","#16161D","#1F1F28","#16161D","#1F1F28","#16161D","#16161D","#2A2A37","#363646","#16161D","#2A2A37","#7E9CD8","#9DB8E8","#DCD7BA","#938AA9","#727169","#DCD7BA","#727169","#2A2A37","#363646","#1F1F28","#363646","#2A2A37","#2D4F67","#DCD7BA","#2A2000","#E6C384","#C34043","#DCD7BA","#DCD7BA","#16161D","#727169","#938AA9"),
    "Kanagawa Dragon":_t("#181616","#181616","#0D0C0C","#181616","#0D0C0C","#181616","#181616","#0D0C0C","#0D0C0C","#282727","#393836","#0D0C0C","#282727","#7E9CD8","#9DB8E8","#C5C9C5","#8A9A7B","#625E5A","#C5C9C5","#625E5A","#282727","#393836","#181616","#393836","#282727","#2D4F67","#C5C9C5","#2A1E00","#E6C384","#C34043","#C5C9C5","#C5C9C5","#0D0C0C","#625E5A","#8A9A7B"),
    "Everforest Dark":_t("#2D353B","#2D353B","#272E33","#272E33","#2D353B","#272E33","#2D353B","#1E2326","#272E33","#3D484D","#475258","#272E33","#3D484D","#A7C080","#C2D89A","#D3C6AA","#9DA9A0","#5C6A72","#D3C6AA","#7A8478","#3D484D","#475258","#2D353B","#475258","#3D484D","#3D484D","#D3C6AA","#1E2A1A","#A7C080","#E67E80","#D3C6AA","#D3C6AA","#272E33","#5C6A72","#9DA9A0"),
    "Horizon Dark":_t("#1C1E26","#1C1E26","#16181F","#16181F","#1C1E26","#16181F","#1C1E26","#16181F","#16181F","#2E303E","#3C3E4D","#16181F","#2E303E","#F43E5C","#F76E87","#D5D8DA","#B7BCC4","#4A4C5E","#D5D8DA","#6C6F93","#2E303E","#3C3E4D","#1C1E26","#3C3E4D","#2E303E","#3C3E4D","#D5D8DA","#2A0A12","#F43E5C","#F09483","#D5D8DA","#D5D8DA","#16181F","#4A4C5E","#6C6F93"),
    "Poimandres":_t("#1B1E28","#1B1E28","#141722","#141722","#1B1E28","#141722","#1B1E28","#0F1117","#141722","#252837","#303347","#141722","#252837","#89DDFF","#A8EEFF","#A6ACCD","#6E738D","#303347","#A6ACCD","#6E738D","#252837","#303347","#1B1E28","#303347","#252837","#303347","#A6ACCD","#002040","#89DDFF","#F085E6","#1B1E28","#A6ACCD","#141722","#303347","#5DE4C7"),
    "Oxocarbon":_t("#161616","#161616","#0F0F0F","#161616","#0F0F0F","#161616","#161616","#0A0A0A","#0F0F0F","#262626","#393939","#0F0F0F","#262626","#78A9FF","#99BEFF","#F2F4F8","#A2A9B0","#525252","#F2F4F8","#A2A9B0","#393939","#525252","#161616","#525252","#393939","#393939","#F2F4F8","#002060","#78A9FF","#FF7EB6","#161616","#F2F4F8","#0F0F0F","#525252","#A2A9B0"),
    "Vesper":_t("#101010","#101010","#0A0A0A","#101010","#0A0A0A","#101010","#101010","#080808","#0A0A0A","#1A1A1A","#222222","#0A0A0A","#1A1A1A","#FAD000","#FFE04D","#FFFFFF","#8B8B8B","#444444","#FFFFFF","#8B8B8B","#222222","#333333","#101010","#333333","#1A1A1A","#333333","#FFFFFF","#2A2000","#FAD000","#F97B58","#FFFFFF","#FFFFFF","#0A0A0A","#444444","#8B8B8B"),
    "Moonlight":_t("#212337","#212337","#191A2A","#191A2A","#212337","#191A2A","#212337","#15162A","#191A2A","#2F3354","#383C60","#191A2A","#2F3354","#82AAFF","#A0C4FF","#C8D3F5","#828BB8","#444A73","#C8D3F5","#444A73","#2F3354","#383C60","#212337","#383C60","#2F3354","#383C60","#C8D3F5","#2A1E55","#82AAFF","#FF757F","#212337","#C8D3F5","#191A2A","#444A73","#828BB8"),
    "Melange Dark":_t("#2A2520","#2A2520","#211D18","#211D18","#2A2520","#211D18","#2A2520","#1A1612","#211D18","#3A3430","#4A4440","#211D18","#3A3430","#ECA673","#F0B88A","#ECE1D7","#B8A898","#6E6560","#ECE1D7","#8E8580","#3A3430","#4A4440","#2A2520","#4A4440","#3A3430","#4A3440","#ECE1D7","#2A1E00","#ECA673","#E06C75","#ECE1D7","#ECE1D7","#211D18","#6E6560","#9A9090"),
    "Monokai Pro":_t("#2D2A2E","#2D2A2E","#221F22","#221F22","#2D2A2E","#221F22","#2D2A2E","#1A1A1A","#221F22","#403E41","#5B595C","#221F22","#403E41","#A9DC76","#C2F094","#FCFCFA","#939293","#727072","#FCFCFA","#727072","#403E41","#5B595C","#2D2A2E","#5B595C","#403E41","#403E41","#FCFCFA","#1E3320","#A9DC76","#FF6188","#FCFCFA","#FCFCFA","#221F22","#5B595C","#939293"),
    "Bluloco Dark":_t("#282C33","#282C33","#21252B","#21252B","#282C33","#21252B","#282C33","#1C2026","#21252B","#31363F","#404652","#21252B","#31363F","#3FC6E0","#60D8F0","#ABB2BF","#636D83","#3B4252","#ABB2BF","#636D83","#31363F","#404652","#282C33","#404652","#31363F","#31363F","#ABB2BF","#002A33","#3FC6E0","#FC4B4E","#282C33","#ABB2BF","#21252B","#404652","#636D83"),
    "Rosebox":_t("#21202E","#21202E","#191826","#191826","#21202E","#191826","#21202E","#141322","#191826","#2C2B3A","#3C3B4A","#191826","#2C2B3A","#D16D9E","#E085B5","#FEFDFF","#9E9CAB","#56546B","#FEFDFF","#6E6C80","#2C2B3A","#3C3B4A","#21202E","#3C3B4A","#2C2B3A","#3C2B4A","#FEFDFF","#2A1040","#D16D9E","#F0605B","#FEFDFF","#FEFDFF","#191826","#56546B","#9E9CAB"),
    "Flexoki Dark":_t("#100F0F","#100F0F","#1C1B1A","#100F0F","#1C1B1A","#100F0F","#100F0F","#080707","#1C1B1A","#282726","#343331","#1C1B1A","#282726","#4385BE","#5B9DD6","#CECDC3","#878580","#575653","#CECDC3","#878580","#343331","#575653","#100F0F","#575653","#282726","#282726","#CECDC3","#002060","#4385BE","#D14D41","#100F0F","#CECDC3","#1C1B1A","#575653","#878580"),
    "Mellow":_t("#1E1E1E","#1E1E1E","#181818","#181818","#1E1E1E","#181818","#1E1E1E","#161616","#181818","#2A2A2A","#383838","#181818","#2A2A2A","#B8A1E3","#CFC0F0","#C9C7CD","#857F8A","#4A4A4A","#C9C7CD","#857F8A","#2A2A2A","#383838","#1E1E1E","#383838","#2A2A2A","#383838","#C9C7CD","#2A1E40","#B8A1E3","#E06C75","#1E1E1E","#C9C7CD","#181818","#4A4A4A","#857F8A"),

    # ── LIGHT (30) -- genuinely distinct personalities ────────────────
    # Clean / neutral
    "NovaPad Light":_t("#F2F2F7","#FFFFFF","#EBEBEB","#DEDEDE","#FFFFFF","#D4D4D8","#FFFFFF","#EBEBEB","#FFFFFF","#D1D1D6","#C7C7CC","#FFFFFF","#E5E5EA","#007AFF","#0063CC","#1C1C1E","#636366","#AEAEB2","#1C1C1E","#6E6E73","#D1D1D6","#C7C7CC","#F2F2F7","#C7C7CC","#D1D1D6","#007AFF","#FFFFFF","#FFDF80","#1C1C1E","#FF9500","#FFFFFF","#1C1C1E","#F0F0F3","#8C8C99","#1C1C1E",dark=False),
    "GitHub Light":_t("#FFFFFF","#FFFFFF","#F6F8FA","#EAEEF2","#FFFFFF","#EAEEF2","#FFFFFF","#F6F8FA","#FFFFFF","#EAEEF2","#D0D7DE","#FFFFFF","#F6F8FA","#0969DA","#0757BA","#24292F","#57606A","#8C959F","#24292F","#57606A","#D0D7DE","#D0D7DE","#F6F8FA","#D0D7DE","#EAEEF2","#DBEAFE","#24292F","#FFF3C0","#24292F","#CF222E","#FFFFFF","#24292F","#F6F8FA","#8C959F","#24292F",dark=False),
    "One Light":_t("#FAFAFA","#FAFAFA","#F0F0F0","#F0F0F0","#FAFAFA","#E8E8E8","#FAFAFA","#E8E8E8","#F0F0F0","#E8E8E8","#D8D8D8","#F0F0F0","#E8E8E8","#4078F2","#5590FF","#383A42","#696C77","#A0A1A7","#383A42","#696C77","#D8D8D8","#C8C8C8","#FAFAFA","#C8C8C8","#E8E8E8","#D0E0FF","#383A42","#FFFFB5","#886300","#E45649","#FAFAFA","#383A42","#F0F0F0","#A0A1A7","#696C77",dark=False),
    "Tomorrow":_t("#FFFFFF","#FFFFFF","#F7F7F7","#EFEFEF","#FFFFFF","#EFEFEF","#FFFFFF","#EFEFEF","#F7F7F7","#EFEFEF","#E0E0E0","#FFFFFF","#F0F0F0","#4271AE","#2F5F8F","#4D4D4C","#8E908C","#AEAEAD","#4D4D4C","#8E908C","#E0E0E0","#D0D0D0","#FFFFFF","#D0D0D0","#EFEFEF","#D6E4FF","#4D4D4C","#FFFFB5","#8B7300","#C82829","#FFFFFF","#4D4D4C","#F7F7F7","#AEAEAD","#8E908C",dark=False),
    # Curated palettes
    "Rose Pine Dawn":_t("#FAF4ED","#FAF4ED","#FFFAF3","#FAF4ED","#FFFAF3","#FAF4ED","#FAF4ED","#F4EDE8","#FFFAF3","#F4EDE8","#DFDAD9","#FFFAF3","#F4EDE8","#907AA9","#A890BB","#575279","#797593","#9893A5","#575279","#797593","#DFDAD9","#CECACD","#FAF4ED","#CECACD","#F4EDE8","#CECACD","#575279","#F0E8FF","#907AA9","#B4637A","#FAF4ED","#575279","#FFFAF3","#9893A5","#797593",dark=False),
    "Catppuccin Latte":_t("#EFF1F5","#EFF1F5","#E6E9EF","#E6E9EF","#EFF1F5","#E6E9EF","#EFF1F5","#DCE0E8","#E6E9EF","#DCE0E8","#CCD0DA","#E6E9EF","#DCE0E8","#8839EF","#9D53EF","#4C4F69","#5C5F77","#9CA0B0","#4C4F69","#6C6F85","#CCD0DA","#BCC0CC","#EFF1F5","#BCC0CC","#CCD0DA","#DDE0FF","#4C4F69","#E8DEFF","#7287FD","#D20F39","#EFF1F5","#4C4F69","#E6E9EF","#9CA0B0","#4C4F69",dark=False),
    "Gruvbox Light":_t("#FBF1C7","#FBF1C7","#EBDBB2","#FBF1C7","#EBDBB2","#FBF1C7","#FBF1C7","#EBDBB2","#EBDBB2","#D5C4A1","#BDAE93","#EBDBB2","#D5C4A1","#D79921","#B57614","#3C3836","#665C54","#928374","#3C3836","#7C6F64","#D5C4A1","#BDAE93","#FBF1C7","#BDAE93","#D5C4A1","#D5C4A1","#3C3836","#FFF3C0","#B57614","#CC241D","#FBF1C7","#3C3836","#EBDBB2","#928374","#665C54",dark=False),
    "Solarized Light":_t("#FDF6E3","#FDF6E3","#EEE8D5","#FDF6E3","#EEE8D5","#FDF6E3","#FDF6E3","#EEE8D5","#EEE8D5","#EEE8D5","#DDD6C1","#EEE8D5","#EEE8D5","#268BD2","#1A72BC","#657B83","#839496","#93A1A1","#586E75","#839496","#D3CDB8","#93A1A1","#FDF6E3","#93A1A1","#EEE8D5","#EEE8D5","#657B83","#FFF3C0","#586E75","#CB4B16","#FDF6E3","#657B83","#EEE8D5","#93A1A1","#586E75",dark=False),
    "Ayu Light":_t("#FAFAFA","#FAFAFA","#F3F4F5","#F0F0F0","#FAFAFA","#F0F0F0","#FAFAFA","#F0F0F0","#FFFFFF","#E7E8E9","#D8D9DA","#FFFFFF","#F0F0F0","#FF9940","#FFB570","#575F66","#ADB5BD","#CDD2D7","#575F66","#ADB5BD","#D8D9DA","#CDD2D7","#FAFAFA","#CDD2D7","#E7E8E9","#FFECCC","#575F66","#FFF0D0","#FF9940","#FF3333","#FAFAFA","#575F66","#F3F4F5","#ADB5BD","#575F66",dark=False),
    "Everforest Light":_t("#FDF6E3","#FDF6E3","#F4EBD0","#FDF6E3","#F4EBD0","#FDF6E3","#FDF6E3","#EADFC0","#F4EBD0","#F0E4CC","#E5D3B0","#F4EBD0","#F0E4CC","#8DA101","#9EBB00","#5C6A72","#829181","#97A99F","#5C6A72","#829181","#E5D3B0","#D8C9A0","#FDF6E3","#D8C9A0","#F0E4CC","#E5D3B0","#5C6A72","#EEF0D0","#8DA101","#F85552","#FDF6E3","#5C6A72","#F4EBD0","#97A99F","#829181",dark=False),
    "Kanagawa Lotus":_t("#F2ECBC","#F2ECBC","#E7DEBB","#F2ECBC","#E7DEBB","#F2ECBC","#F2ECBC","#DDD5AF","#E7DEBB","#E7DEBB","#D5CCA3","#E7DEBB","#E7DEBB","#766B90","#8C7FA8","#545464","#716E61","#8A8980","#545464","#716E61","#D5CCA3","#CCC3A0","#F2ECBC","#CCC3A0","#E7DEBB","#D5CCA3","#545464","#EDE8D0","#766B90","#C84053","#F2ECBC","#545464","#E7DEBB","#8A8980","#716E61",dark=False),
    "Flexoki Light":_t("#FFFCF0","#FFFCF0","#F2F0E5","#FFFCF0","#F2F0E5","#FFFCF0","#FFFCF0","#E8E4D9","#F2F0E5","#E8E4D9","#DAD4C4","#F2F0E5","#E8E4D9","#4385BE","#5B9DD6","#100F0F","#6F6E69","#B7B5AC","#100F0F","#6F6E69","#DAD4C4","#CECDC3","#FFFCF0","#CECDC3","#E8E4D9","#DADAFF","#100F0F","#FFEFC0","#D0A215","#AF3029","#FFFCF0","#100F0F","#F2F0E5","#B7B5AC","#6F6E69",dark=False),
    # Coloured/tinted backgrounds
    "Arctic":_t("#ECEFF4","#ECEFF4","#E5E9F0","#ECEFF4","#FFFFFF","#E5E9F0","#ECEFF4","#D8DEE9","#FFFFFF","#D8DEE9","#BEC7D5","#FFFFFF","#E5E9F0","#5E81AC","#4170A0","#2E3440","#4C566A","#8090A8","#2E3440","#4C566A","#BEC7D5","#ADBACB","#ECEFF4","#ADBACB","#D8DEE9","#C5D8F0","#2E3440","#D8F0FF","#5E81AC","#BF616A","#ECEFF4","#2E3440","#E5E9F0","#8090A8","#4C566A",dark=False),
    "Mint":_t("#F0FAF5","#F0FAF5","#E4F5EC","#F0FAF5","#FFFFFF","#E4F5EC","#F0FAF5","#D4EDE0","#FFFFFF","#D4EDE0","#B8DCC8","#FFFFFF","#E4F5EC","#2D8653","#3A9E65","#1A3A2A","#4A7060","#88B0A0","#1A3A2A","#4A7060","#B8DCC8","#A0CCBB","#F0FAF5","#A0CCBB","#D4EDE0","#B8EDD0","#1A3A2A","#FFFFD0","#2D8653","#C0392B","#F0FAF5","#1A3A2A","#E4F5EC","#88B0A0","#4A7060",dark=False),
    "Peach":_t("#FFF8F0","#FFF8F0","#FFF0E0","#FFF8F0","#FFFFFF","#FFF0E0","#FFF8F0","#FFDFC0","#FFFFFF","#FFDFC0","#FFCC99","#FFFFFF","#FFF0E0","#D4560A","#E06820","#3D1A00","#8A5030","#C09070","#3D1A00","#8A5030","#FFCC99","#FFBB80","#FFF8F0","#FFBB80","#FFDFC0","#FFDFC0","#3D1A00","#FFFFF0","#D4560A","#CC2200","#FFF8F0","#3D1A00","#FFF0E0","#C09070","#8A5030",dark=False),
    "Lavender":_t("#F8F4FF","#F8F4FF","#F0E8FF","#F8F4FF","#FFFFFF","#F0E8FF","#F8F4FF","#E0D0F8","#FFFFFF","#E0D0F8","#C8B0F0","#FFFFFF","#F0E8FF","#7C4DFF","#9060FF","#2A1060","#6040A0","#A890D0","#2A1060","#6040A0","#C8B0F0","#B898E8","#F8F4FF","#B898E8","#E0D0F8","#D8C8FF","#2A1060","#FFFFF0","#7C4DFF","#C0185A","#F8F4FF","#2A1060","#F0E8FF","#A890D0","#6040A0",dark=False),
    "Sakura":_t("#FFF5F7","#FFF5F7","#FFE8EE","#FFF5F7","#FFFFFF","#FFE8EE","#FFF5F7","#FFD0DC","#FFFFFF","#FFD0DC","#FFC0CC","#FFFFFF","#FFE8EE","#C0185A","#D4306A","#3A0818","#8A3858","#C890A8","#3A0818","#8A3858","#FFC0CC","#FFAABB","#FFF5F7","#FFAABB","#FFD0DC","#FFD0E8","#3A0818","#FFFFF0","#C0185A","#8B0000","#FFF5F7","#3A0818","#FFE8EE","#C890A8","#8A3858",dark=False),
    "Fog":_t("#F3F5F7","#F3F5F7","#E9EDF1","#F3F5F7","#FFFFFF","#E9EDF1","#F3F5F7","#D9DFE6","#FFFFFF","#D9DFE6","#C0CAD4","#FFFFFF","#E9EDF1","#3B6EA5","#4A80BB","#1E2D3A","#526070","#8898A8","#1E2D3A","#526070","#C0CAD4","#AABAC6","#F3F5F7","#AABAC6","#D9DFE6","#C8DDF0","#1E2D3A","#FFFFF0","#3B6EA5","#AA2020","#F3F5F7","#1E2D3A","#E9EDF1","#8898A8","#526070",dark=False),
    # Warm organic
    "Linen":_t("#FAF0E6","#FAF0E6","#F2E8DA","#FAF0E6","#FFFFFF","#F2E8DA","#FAF0E6","#E8D8C8","#FFFFFF","#E8D8C8","#D4C4B0","#FFFFFF","#F2E8DA","#5C4A32","#7A6040","#2A1A08","#6A5040","#B0988A","#2A1A08","#6A5040","#D4C4B0","#C0B098","#FAF0E6","#C0B098","#E8D8C8","#E0D0B8","#2A1A08","#FFFFD8","#5C4A32","#A02020","#FAF0E6","#2A1A08","#F2E8DA","#B0988A","#6A5040",dark=False),
    "Sandstone":_t("#FAF3E8","#FAF3E8","#F2E8D8","#FAF3E8","#FFFFFF","#F2E8D8","#FAF3E8","#E8D8C4","#FFFFFF","#E8D8C4","#D4C0A8","#FFFFFF","#F2E8D8","#8B5E3C","#A07050","#3A2010","#7A5840","#B09078","#3A2010","#7A5840","#D4C0A8","#C0A890","#FAF3E8","#C0A890","#E8D8C4","#F0D8B8","#3A2010","#FFFFF0","#8B5E3C","#B02020","#FAF3E8","#3A2010","#F2E8D8","#B09078","#7A5840",dark=False),
    "Parchment":_t("#F5EFDC","#F5EFDC","#EDE5D0","#F5EFDC","#F8F3E8","#EDE5D0","#F5EFDC","#E0D5BC","#F8F3E8","#E0D5BC","#C8BC9C","#F8F3E8","#EDE5D0","#704214","#8B5520","#2C1A00","#6A5038","#B09878","#2C1A00","#6A5038","#C8BC9C","#B8A88C","#F5EFDC","#B8A88C","#E0D5BC","#E8D8B8","#2C1A00","#FFFFF0","#704214","#991A1A","#F5EFDC","#2C1A00","#EDE5D0","#B09878","#6A5038",dark=False),
    "Wheat":_t("#FFFAED","#FFFAED","#FFF4D8","#FFFAED","#FFFFFF","#FFF4D8","#FFFAED","#FFE8B0","#FFFFFF","#FFE8B0","#FFD880","#FFFFFF","#FFF4D8","#B07820","#C88C30","#2A1A00","#7A5820","#C0A070","#2A1A00","#7A5820","#FFD880","#FFC060","#FFFAED","#FFC060","#FFE8B0","#FFE8A0","#2A1A00","#FFFFF0","#B07820","#C02020","#FFFAED","#2A1A00","#FFF4D8","#C0A070","#7A5820",dark=False),
    "Copper":_t("#FBF5EE","#FBF5EE","#F5EDE2","#FBF5EE","#FFFFFF","#F5EDE2","#FBF5EE","#EBE0D0","#FFFFFF","#EBE0D0","#D8C8B4","#FFFFFF","#F5EDE2","#B5540A","#C86818","#2A1000","#7A5030","#C0A080","#2A1000","#7A5030","#D8C8B4","#C4B098","#FBF5EE","#C4B098","#EBE0D0","#F0D8C0","#2A1000","#FFFFF0","#B5540A","#AA1818","#FBF5EE","#2A1000","#F5EDE2","#C0A080","#7A5030",dark=False),
    # Nature/cool
    "Forest Mist":_t("#F4F9F2","#F4F9F2","#EBF5E8","#F4F9F2","#FFFFFF","#EBF5E8","#F4F9F2","#D8EDD4","#FFFFFF","#D8EDD4","#BECEBB","#FFFFFF","#EBF5E8","#2E7D4E","#3A9060","#102818","#3A6048","#7AA090","#102818","#3A6048","#BECEBB","#A8BEA6","#F4F9F2","#A8BEA6","#D8EDD4","#C8E8D0","#102818","#FFFFF0","#2E7D4E","#B02020","#F4F9F2","#102818","#EBF5E8","#7AA090","#3A6048",dark=False),
    "Cobalt Light":_t("#F0F4FF","#FFFFFF","#E8EEFF","#F0F4FF","#FFFFFF","#E8EEFF","#FFFFFF","#DCE4FF","#FFFFFF","#DCE4FF","#B8C8FF","#FFFFFF","#E8EEFF","#1A40CC","#0F30BB","#0A1040","#405080","#8898C8","#0A1040","#405080","#B8C8FF","#A0B4F0","#F0F4FF","#A0B4F0","#DCE4FF","#CCE0FF","#0A1040","#FFFFF0","#1A40CC","#CC1A1A","#FFFFFF","#0A1040","#E8EEFF","#8898C8","#405080",dark=False),
    "Ink":_t("#FAFAF8","#FAFAF8","#F2F2F0","#FAFAF8","#FFFFFF","#F2F2F0","#FAFAF8","#E8E8E4","#FFFFFF","#E8E8E4","#D0D0C8","#FFFFFF","#F2F2F0","#101010","#303030","#080808","#404040","#888880","#080808","#404040","#D0D0C8","#C0C0B8","#FAFAF8","#C0C0B8","#E8E8E4","#D8D8D0","#080808","#FFFFF0","#101010","#880000","#FAFAF8","#080808","#F2F2F0","#888880","#404040",dark=False),
    "Dusk":_t("#FFF2EE","#FFF2EE","#FFE8E0","#FFF2EE","#FFFFFF","#FFE8E0","#FFF2EE","#FFD8CC","#FFFFFF","#FFD8CC","#FFC0B0","#FFFFFF","#FFE8E0","#D44000","#E05010","#3A1000","#8A4828","#C09088","#3A1000","#8A4828","#FFC0B0","#FFAA98","#FFF2EE","#FFAA98","#FFD8CC","#FFD8C0","#3A1000","#FFFFF0","#D44000","#990000","#FFF2EE","#3A1000","#FFE8E0","#C09088","#8A4828",dark=False),
}

DEFAULT_THEME = "NovaPad Dark"
THEME_NAMES = list(THEMES.keys())

_QSS = """
QWidget {{
    background-color: {bg_app};
    color: {fg_primary};
    font-family: -apple-system, "Segoe UI Variable", "Segoe UI", "SF Pro Text", "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
    selection-background-color: {sel_bg};
    selection-color: {sel_fg};
    outline: none;
    border: none;
}}
QMainWindow {{ background-color: {bg_window}; }}
QMenuBar {{ background-color: {bg_toolbar}; color: {fg_primary}; border-bottom: 1px solid {border}; padding: 1px 4px; spacing: 2px; }}
QMenuBar::item {{ background: transparent; padding: 5px 10px; border-radius: 5px; }}
QMenuBar::item:selected, QMenuBar::item:pressed {{ background-color: {bg_hover}; }}
QMenu {{ background-color: {bg_menu}; color: {fg_primary}; border: 1px solid {border}; border-radius: 10px; padding: 5px 0; }}
QMenu::item {{ padding: 6px 28px 6px 20px; border-radius: 5px; margin: 1px 5px; }}
QMenu::item:selected {{ background-color: {accent}; color: #FFFFFF; }}
QMenu::item:disabled {{ color: {fg_muted}; }}
QMenu::separator {{ height: 1px; background: {separator}; margin: 4px 10px; }}
QToolBar {{ background-color: {bg_toolbar}; border: none; border-bottom: 1px solid {border}; padding: 3px 6px; spacing: 2px; }}
QToolBar::separator {{ width: 1px; background: {separator}; margin: 4px 3px; }}
QToolButton {{ background: transparent; color: {fg_primary}; border: none; border-radius: 5px; padding: 3px 4px; font-size: 11px; min-width: 22px; min-height: 22px; }}
QToolButton:hover {{ background-color: {bg_hover}; }}
QToolButton:pressed {{ background-color: {bg_pressed}; }}
QToolButton:checked {{ background-color: {bg_pressed}; color: {accent}; }}
QTabWidget::pane {{ border: none; background: {bg_editor}; }}
QTabWidget::tab-bar {{ left: 0; }}
QTabBar {{ background: {bg_tab_bar}; }}
QTextEdit {{ background-color: {bg_editor}; color: {fg_primary}; border: none; padding: 6px 2px 6px 2px; selection-background-color: {sel_bg}; selection-color: {sel_fg}; }}
QScrollBar:vertical {{ background: {scrollbar_bg}; width: 10px; margin: 0; border-radius: 5px; }}
QScrollBar::handle:vertical {{ background: {scrollbar_handle}; border-radius: 4px; min-height: 24px; margin: 1px; }}
QScrollBar::handle:vertical:hover {{ background: {fg_muted}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{ background: {scrollbar_bg}; height: 10px; margin: 0; border-radius: 5px; }}
QScrollBar::handle:horizontal {{ background: {scrollbar_handle}; border-radius: 4px; min-width: 24px; margin: 1px; }}
QScrollBar::handle:horizontal:hover {{ background: {fg_muted}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
QStatusBar {{ background: {bg_statusbar}; color: {fg_secondary}; border-top: 1px solid {border}; font-size: 11px; padding: 1px 8px; }}
QStatusBar::item {{ border: none; }}
QWidget#FindBar {{ background-color: {bg_toolbar}; border-top: 1px solid {border}; }}
QLineEdit {{ background: {bg_input}; color: {fg_primary}; border: 1.5px solid {border_input}; border-radius: 6px; padding: 4px 9px; font-size: 13px; selection-background-color: {sel_bg}; }}
QLineEdit:focus {{ border-color: {accent}; }}
QLineEdit:disabled {{ color: {fg_muted}; background: {bg_app}; }}
QPushButton {{ background: {bg_button}; color: {fg_primary}; border: 1px solid {border}; border-radius: 6px; padding: 4px 12px; font-size: 12px; font-weight: 500; min-height: 26px; }}
QPushButton:hover {{ background: {bg_hover}; }}
QPushButton:pressed {{ background: {bg_pressed}; }}
QCheckBox {{ color: {fg_primary}; spacing: 6px; }}
QCheckBox::indicator {{ width: 15px; height: 15px; border: 1.5px solid {border_input}; border-radius: 4px; background: {bg_input}; }}
QCheckBox::indicator:checked {{ background: {accent}; border-color: {accent}; }}
QComboBox {{ background: {bg_button}; color: {fg_primary}; border: 1px solid {border}; border-radius: 6px; padding: 4px 10px; min-width: 80px; }}
QComboBox::drop-down {{ border: none; width: 20px; }}
QComboBox QAbstractItemView {{ background: {bg_menu}; color: {fg_primary}; border: 1px solid {border}; border-radius: 6px; selection-background-color: {accent}; selection-color: #FFFFFF; padding: 4px; }}
QLabel {{ background: transparent; color: {fg_primary}; }}
QDialog {{ background: {bg_window}; }}
QMessageBox {{ background: {bg_window}; }}
"""


def apply_titlebar_color(window, bg_hex: str):
    """Set Windows 10/11 title bar color using DwmSetWindowAttribute."""
    import sys
    if sys.platform != "win32":
        return
    try:
        import ctypes
        import ctypes.wintypes
        hwnd = int(window.winId())
        # Convert #RRGGBB to COLORREF (0x00BBGGRR)
        r = int(bg_hex[1:3], 16)
        g = int(bg_hex[3:5], 16)
        b = int(bg_hex[5:7], 16)
        colorref = ctypes.c_uint32(b << 16 | g << 8 | r)
        DWMWA_CAPTION_COLOR = 35
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_CAPTION_COLOR,
            ctypes.byref(colorref),
            ctypes.sizeof(colorref),
        )
    except Exception:
        pass  # silently ignore on older Windows or if DWM unavailable


class ThemeManager:
    _name: str = DEFAULT_THEME

    @classmethod
    def apply(cls, app: QApplication, name: str):
        if name not in THEMES:
            name = DEFAULT_THEME
        cls._name = name
        t = THEMES[name]
        # Compute a WCAG-correct selection foreground before building the stylesheet
        # so selection-color in every widget is always readable.
        sel_bg = QColor(t["sel_bg"])
        sel_fg = QColor(t["sel_fg"])
        def _luma(c):
            def _lin(v):
                v = v / 255.0
                return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
            return 0.2126*_lin(c.red()) + 0.7152*_lin(c.green()) + 0.0722*_lin(c.blue())
        def _contrast(a, b):
            la, lb = _luma(a), _luma(b)
            if la < lb: la, lb = lb, la
            return (la + 0.05) / (lb + 0.05)
        if _contrast(sel_bg, sel_fg) < 4.5:
            sel_fg = QColor("#FFFFFF") if _luma(sel_bg) < 0.5 else QColor("#000000")
        t_with_contrast = {**t, "sel_fg": sel_fg.name()}
        app.setStyleSheet(_QSS.format(**t_with_contrast))
        cls._set_palette(app, t)

    @staticmethod
    def _set_palette(app, t):
        p = QPalette()
        p.setColor(QPalette.ColorRole.Window,          QColor(t["bg_window"]))
        p.setColor(QPalette.ColorRole.WindowText,      QColor(t["fg_primary"]))
        p.setColor(QPalette.ColorRole.Base,            QColor(t["bg_editor"]))
        p.setColor(QPalette.ColorRole.AlternateBase,   QColor(t["bg_toolbar"]))
        p.setColor(QPalette.ColorRole.Text,            QColor(t["fg_primary"]))
        p.setColor(QPalette.ColorRole.Button,          QColor(t["bg_button"]))
        p.setColor(QPalette.ColorRole.ButtonText,      QColor(t["fg_primary"]))
        p.setColor(QPalette.ColorRole.Highlight,       QColor(t["accent"]))
        p.setColor(QPalette.ColorRole.HighlightedText, QColor(t["sel_fg"]))
        p.setColor(QPalette.ColorRole.PlaceholderText, QColor(t["fg_muted"]))
        p.setColor(QPalette.ColorRole.Link,            QColor(t["accent"]))
        app.setPalette(p)

    @classmethod
    def current(cls) -> dict:
        return THEMES.get(cls._name, THEMES[DEFAULT_THEME])

    @classmethod
    def current_name(cls) -> str:
        return cls._name

    @classmethod
    def is_dark(cls) -> bool:
        return cls.current().get("is_dark", True)

    @classmethod
    def find_colors(cls) -> dict:
        t = cls.current()
        return {"match_bg": t["find_match_bg"], "match_fg": t["find_match_fg"],
                "cur_bg": t["find_cur_bg"], "cur_fg": t["find_cur_fg"]}
