# Historical filename retained for the existing preflight entry point.
# Heuristic lexer: literal commands, continuations, substitutions and quoted SSH.
# Each curl invocation has its own deadline; echo/printf quoted prose is ignored.
# Computed command names and options hidden in shell arrays require manual review.
BEGIN { CR = sprintf("%c", 13) }
function check_command(args, n,    first,i,value,bounded) {
    first = 1
    while (first <= n && (args[first] ~ /^(if|then|elif|do|exec|command|!)$/ ||
                         args[first] ~ /^[A-Za-z_][A-Za-z_0-9]*=/)) first++
    if (args[first] == "ssh") {
        # SSH executes its remote command argument through the remote shell.
        if (n > first) scan(args[n])
        return
    }
    if (args[first] != "curl") return
    calls++
    bounded = 0
    for (i = first + 1; i <= n; i++) {
        value = ""
        if (args[i] == "--max-time" || args[i] == "-m") value = args[i+1]
        else if (args[i] ~ /^--max-time=/) value = substr(args[i], 12)
        else if (args[i] ~ /^-m[0-9]/) value = substr(args[i], 3)
        if (value == "") continue
        # Literal zero disables curl's deadline. Dynamic variables need runtime review.
        if (value ~ /^[0-9]+([.][0-9]+)?$/ && value + 0 <= 0) continue
        bounded = 1
    }
    if (!bounded) printf "BAD %s:%d\n", FILENAME, ln
}
function scan(text,    args,n,word,quote,escaped,i,ch,nextch,substitution,start,depth) {
    n = 0; word = ""; quote = ""; escaped = 0
    for (i = 1; i <= length(text); i++) {
        ch = substr(text,i,1); nextch = substr(text,i+1,1)
        if (escaped) { word = word ch; escaped = 0; continue }
        if (ch == "\\" && quote != "\047") { escaped = 1; continue }
        if (ch == "$" && nextch == "(" && quote != "\047") {
            start = i + 2; depth = 1; i++
            while (++i <= length(text) && depth) {
                ch = substr(text,i,1)
                if (ch == "(") depth++
                if (ch == ")") depth--
            }
            substitution = substr(text,start,i-start-1)
            scan(substitution)
            word = word "SUBSTITUTION"
            i--
            continue
        }
        if (quote != "") {
            if (ch == quote) quote = ""
            else word = word ch
            continue
        }
        if (ch == "\042" || ch == "\047") { quote = ch; continue }
        if (ch == "#" && word == "") break
        if (ch ~ /[[:space:];|&()]/) {
            if (word != "") { args[++n] = word; word = "" }
            if (ch !~ /[[:space:]]/) { check_command(args,n); delete args; n = 0 }
        } else word = word ch
    }
    if (word != "") args[++n] = word
    check_command(args,n)
}
function emit() {
    scan(buf)
    buf = ""; ln = 0
}
{
    line = $0
    if (length(line) > 0 && substr(line,length(line)) == CR)
        line = substr(line,1,length(line)-1)
    if (buf == "") ln = FNR
    if (line ~ /\\$/) { sub(/\\$/, "", line); buf = buf " " line; next }
    buf = buf " " line
    emit()
}
END { if (buf != "") emit(); printf "COUNT %d\n", calls }
