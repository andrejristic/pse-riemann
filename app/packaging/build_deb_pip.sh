#!/usr/bin/env bash
# Build the PSE Riemann .deb WITHOUT PyInstaller (alternative to build_deb.sh, which CI uses).
#
#     ./packaging/build_deb_pip.sh            build
#     ./packaging/build_deb_pip.sh --install  build, then install with dpkg
#
# Layout of the installed package:
#     /opt/pse-riemann/app/      the application code
#     /opt/pse-riemann/lib/      bundled Python deps (pip --target, relocatable)
#     /usr/bin/pse-riemann       launcher
#     /usr/share/applications/   desktop entry
#     /usr/share/icons/...       icon
#
# Why every Python dep is bundled rather than declared as apt Depends:
# `python3-pyside6` does not exist in the Mint/Ubuntu archive at all, and the
# archive's mpmath (1.2.1) and matplotlib (3.6.3) are older than the versions
# this was actually tested against. Mixing tested and untested versions on the
# eve of a twenty-day trip is exactly the wrong trade, so the package carries
# its own and depends only on system C libraries. `pip --target` rather than a
# venv, because a venv bakes absolute paths at creation and a .deb must be
# relocatable.
#
# The vault does NOT go in the package. /opt is not writable by you, so a
# packaged install keeps the vault in ~/.local/share/pse-riemann/vault
# (see pse_r/config._default_vault).
set -euo pipefail
cd "$(dirname "$0")/.."          # -> app/

# Variant (plan F10):
#   full     = B  package "pse-riemann"          sympy + scipy + llama-cpp (SVE)
#   lean     = A  package "pse-riemann-lean"     sympy + llama-cpp, BEZ scipy
#                 (Provides/Conflicts/Replaces pse-riemann: never both at once)
#   research = C  package "pse-riemann-research" ADD-ON: only scipy, into
#                 /opt/pse-riemann/lib-research; Depends: pse-riemann (A or B).
#                 Installed on top of A it gives what B has.
# First argument picks the variant; no argument = full.
VARIANT="full"
case "${1:-}" in
    full|lean|research) VARIANT="$1"; shift ;;
esac

APP="pse-riemann"
VERSION="$(python3 - <<'PY'
import re, pathlib
t = pathlib.Path("pse_r/config.py").read_text()
print(re.search(r'VERSION\s*=\s*"([^"]+)"', t).group(1))
PY
)"
ARCH="$(dpkg --print-architecture)"
BUILD="$(pwd)/build"
# full keeps the plain name (it is THE package); lean/research get a suffix so
# builds sit side by side without overwriting.
SUFFIX=""
[ "$VARIANT" != "full" ] && SUFFIX="-$VARIANT"
STAGE="$BUILD/${APP}${SUFFIX}_${VERSION}_${ARCH}"
OUT="$BUILD/${APP}${SUFFIX}_${VERSION}_${ARCH}.deb"

# The interpreter used to fetch wheels. Prefer the venv (it already has pip and
# matches the host's Python), fall back to system python3.
PIP_PY="./.venv/bin/python"
[ -x "$PIP_PY" ] || PIP_PY="python3"
PYVER="$($PIP_PY -c 'import sys;print("%d.%d"%sys.version_info[:2])')"

PKG="$APP"
[ "$VARIANT" = "lean" ] && PKG="$APP-lean"

# ------------------------------------------------ C: research add-on ----
if [ "$VARIANT" = "research" ]; then
    PKG="$APP-research"
    rm -rf "$STAGE"
    mkdir -p "$STAGE/DEBIAN" "$STAGE/opt/$APP/lib-research" "$STAGE/usr/share/doc/$PKG"
    echo "→ (research dodatak) samo scipy u /opt/$APP/lib-research…"
    NUMPY_V="$("$PIP_PY" -c 'import numpy;print(numpy.__version__)')"
    "$PIP_PY" -m pip install --quiet --target "$STAGE/opt/$APP/lib-research" \
        --no-compile --no-deps scipy
    find "$STAGE/opt/$APP/lib-research" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
    rm -rf "$STAGE/opt/$APP/lib-research"/*.dist-info/RECORD 2>/dev/null || true
    INSTALLED_KB="$(du -sk "$STAGE" | cut -f1)"
    cat > "$STAGE/DEBIAN/control" <<CTRL
Package: $PKG
Version: $VERSION
Section: science
Priority: optional
Architecture: $ARCH
Depends: pse-riemann (= $VERSION)
Installed-Size: $INSTALLED_KB
Maintainer: Andrej Ristic <andrej.s.ristic@gmail.com>
Description: PSE Riemann - dodatak za istrazivaca metoda (scipy)
 Dodatak za pse-riemann-lean: donosi scipy u /opt/pse-riemann/lib-research,
 koji launcher automatski dodaje na putanju. Lean + ovaj dodatak = puna
 verzija. Pravljen uz numpy $NUMPY_V iz osnovnog paketa.
CTRL
    echo "Dodatak za istrazivaca metoda (scipy). Zavisi od pse-riemann (lean ili full)." \
        > "$STAGE/usr/share/doc/$PKG/README"
    find "$STAGE" -type d -exec chmod 755 {} +
    OUT="$BUILD/${PKG}_${VERSION}_${ARCH}.deb"
    fakeroot dpkg-deb --build -Zxz "$STAGE" "$OUT" >/dev/null
    echo "✅ $OUT"; ls -lh "$OUT" | awk '{print "   velicina: " $5}'
    exit 0
fi

echo "PSE Riemann .deb"
echo "  verzija   : $VERSION"
echo "  arch      : $ARCH"
echo "  python    : $PYVER  ($PIP_PY)"
echo "  staging   : $STAGE"
echo

rm -rf "$STAGE"
mkdir -p "$STAGE/DEBIAN" \
         "$STAGE/opt/$APP/app" \
         "$STAGE/opt/$APP/lib" \
         "$STAGE/usr/bin" \
         "$STAGE/usr/share/applications" \
         "$STAGE/usr/share/icons/hicolor/256x256/apps" \
         "$STAGE/usr/share/doc/$APP"

# ---------------------------------------------------------------- code ----
echo "→ kopiram kod…"
cp -r pse_r main.py run.sh setup.sh requirements.txt "$STAGE/opt/$APP/app/"
# marker: tells config.py this is an installed package, so the vault goes to
# ~/.local/share instead of next to read-only code under /opt
touch "$STAGE/opt/$APP/app/.packaged"   # must sit beside main.py: config looks at APP_ROOT
find "$STAGE/opt/$APP/app" -name '__pycache__' -type d -prune -exec rm -rf {} +
find "$STAGE/opt/$APP/app" -name '*.pyc' -delete
cp -r packaging "$STAGE/opt/$APP/app/" 2>/dev/null || true
# bundle the extracted method packs so the packaged app can run the acceptance
# reproduction (plan F10: test prihvatanja na pravoj aplikaciji)
if [ -d ../research/qrh-2026-10/method-packs ]; then
    cp -r ../research/qrh-2026-10/method-packs "$STAGE/opt/$APP/app/method-packs"
fi
for f in ../VODIC-SR.md ../GUIDE-EN.md ../README.md; do
    [ -f "$f" ] && cp "$f" "$STAGE/usr/share/doc/$APP/"
done

# ------------------------------------------------------------- deps ----
# Base (A i B): GUI + numerika + sympy (metode: egzaktni polinomi) + llama-cpp
# (lokalni GGUF: offline glavni/skeptik je dio dogovora). B dodaje scipy.
BASE_DEPS="mpmath numpy matplotlib sympy"
case "$VARIANT" in
    full)     EXTRA="scipy" ;;
    lean)     EXTRA="" ;;
esac
echo "→ varijanta: $VARIANT · pakujem PySide6 $BASE_DEPS $EXTRA (nista od apt-a)…"
"$PIP_PY" -m pip install --quiet --target "$STAGE/opt/$APP/lib" \
    --no-compile PySide6-Essentials $BASE_DEPS $EXTRA \
    || "$PIP_PY" -m pip install --quiet --target "$STAGE/opt/$APP/lib" \
       --no-compile PySide6 $BASE_DEPS $EXTRA
echo "→ dodajem llama-cpp-python (CPU wheel; lokalni GGUF)…"
"$PIP_PY" -m pip install --quiet --target "$STAGE/opt/$APP/lib" --no-compile \
    --only-binary :all: --no-deps \
    --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu \
    llama-cpp-python diskcache jinja2 MarkupSafe typing_extensions
"$PIP_PY" - "$STAGE/opt/$APP/lib" <<'PYCHK'
import sys; sys.path.insert(0, sys.argv[1]); import llama_cpp
print("   llama-cpp", llama_cpp.__version__, "OK")
PYCHK
# trim what a desktop app on 4 GB will never use
rm -rf "$STAGE/opt/$APP/lib"/PySide6/Qt/qml \
       "$STAGE/opt/$APP/lib"/PySide6/Qt/translations \
       "$STAGE/opt/$APP/lib"/*.dist-info/RECORD \
       "$STAGE/opt/$APP/lib"/PySide6/examples 2>/dev/null || true
find "$STAGE/opt/$APP/lib" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true

# ------------------------------------------------------------- icon ----
echo "→ pravim ikonu…"
"$PIP_PY" packaging/make_icon.py \
    "$STAGE/usr/share/icons/hicolor/256x256/apps/$APP.png" 256 >/dev/null

# --------------------------------------------------------- launcher ----
cat > "$STAGE/usr/bin/$APP" <<'LAUNCH'
#!/usr/bin/env bash
# PSE Riemann launcher (packaged install).
set -euo pipefail
ROOT="/opt/pse-riemann"
# Bundled deps first. PYTHONPATH is prepended, never replaced, so a user who
# has their own PYTHONPATH keeps it.
LIBS="$ROOT/lib"
# research add-on (C), if installed, brings scipy here
[ -d "$ROOT/lib-research" ] && LIBS="$LIBS:$ROOT/lib-research"
export PYTHONPATH="$LIBS${PYTHONPATH:+:$PYTHONPATH}"
exec python3 "$ROOT/app/main.py" "$@"
LAUNCH
chmod 755 "$STAGE/usr/bin/$APP"

# ------------------------------------------------------ desktop entry ----
cat > "$STAGE/usr/share/applications/$APP.desktop" <<DESK
[Desktop Entry]
Type=Application
Version=1.0
Name=PSE Riemann
GenericName=Riemann zeta study assistant
Comment=Asistent za izučavanje Rimanove zeta funkcije
Exec=$APP
Icon=$APP
Terminal=false
Categories=Education;Science;Math;
Keywords=riemann;zeta;math;matematika;
StartupNotify=true
DESK

# -------------------------------------------------------------- meta ----
INSTALLED_KB="$(du -sk "$STAGE" | cut -f1)"
cat > "$STAGE/DEBIAN/control" <<CTRL
Package: $PKG
Version: $VERSION
Section: science
Priority: optional
Architecture: $ARCH
Depends: python3 (>= 3.10), libgl1, libegl1, libxkbcommon0, libdbus-1-3, libfontconfig1, libxcb-cursor0
$( [ "$VARIANT" = "lean" ] && printf 'Provides: pse-riemann (= %s)\nConflicts: pse-riemann\nReplaces: pse-riemann' "$VERSION" || printf 'Conflicts: pse-riemann-lean\nReplaces: pse-riemann-lean' )
Recommends: ufw
Installed-Size: $INSTALLED_KB
Maintainer: Andrej Ristic <andrej.s.ristic@gmail.com>
Description: Asistent za izucavanje Rimanove zeta funkcije
 Desktop aplikacija za dvadesetodnevno izucavanje Rimanove zeta funkcije,
 gradjena na PSE kernelu i za rad na tudjim mrezama.
 .
  * Lab: dvanaest reproducibilnih mpmath eksperimenata (nule, Gramov zakon,
    eksplicitna formula, GUE statistika, Robinov kriterijum ...)
  * Kapija: jedan put upisa; COMPUTED trazi lab-run i sha256 skripte, CITED
    trazi razrjesiv izvor, tvrdnja o dokazu RH se odbija
  * Guardian: sav saobracaj kroz jednu funkciju, default-deny allowlist,
    TLS SPKI pinning, kljucevi samo model API-jima
  * SHARED_LIB: glas samo operateru, misije, vrata za metode (sistem
    eksponenata kao podatak + test reprodukcije), cuvari izvjestaja
  * Glavni AI + nezavisni skeptik (cloud ili lokalni GGUF, sa limiterima)
 .
 Varijanta: $VARIANT (full=sympy+scipy+llama-cpp, lean=bez scipy).
 Vault se cuva u ~/.local/share/pse-riemann/vault.
CTRL

cat > "$STAGE/DEBIAN/postinst" <<'POST'
#!/bin/sh
set -e
if [ "$1" = "configure" ]; then
    command -v update-desktop-database >/dev/null 2>&1 && \
        update-desktop-database -q /usr/share/applications || true
    command -v gtk-update-icon-cache >/dev/null 2>&1 && \
        gtk-update-icon-cache -q -f /usr/share/icons/hicolor || true
    echo ""
    echo "PSE Riemann je instaliran."
    echo "  pokretanje : pse-riemann        (ili iz menija)"
    echo "  provjera   : pse-riemann --selftest"
    echo "  vault      : ~/.local/share/pse-riemann/vault"
    echo ""
    echo "PRIJE PUTA: pokreni jednom sa mreze kojoj vjerujes i uradi"
    echo "  Corpus -> Skupi  i  Guardian -> Test mreze."
    echo "  TLS pinovi se uce pri prvom kontaktu; ako je prvi kontakt"
    echo "  na hotelskom WiFi-ju, zapamtices presretaca."
    echo ""
fi
exit 0
POST
chmod 755 "$STAGE/DEBIAN/postinst"

cat > "$STAGE/DEBIAN/postrm" <<'PRM'
#!/bin/sh
set -e
if [ "$1" = "purge" ] || [ "$1" = "remove" ]; then
    command -v update-desktop-database >/dev/null 2>&1 && \
        update-desktop-database -q /usr/share/applications || true
    echo "Napomena: vault i kljucevi NISU obrisani."
    echo "  ~/.local/share/pse-riemann/   (vault)"
    echo "  ~/.config/pse-riemann/        (kljucevi, podesavanja)"
fi
exit 0
PRM
chmod 755 "$STAGE/DEBIAN/postrm"

# ------------------------------------------------------------- build ----
echo "→ gradim paket…"
find "$STAGE" -type d -exec chmod 755 {} +
find "$STAGE/opt/$APP/app" -name '*.sh' -exec chmod 755 {} +
fakeroot dpkg-deb --build -Zxz "$STAGE" "$OUT" >/dev/null

echo
echo "✅ $OUT"
ls -lh "$OUT" | awk '{print "   velicina: " $5}'
echo "   instalirano: $((INSTALLED_KB / 1024)) MB"
echo
echo "Instalacija:"
echo "   sudo apt install $OUT"
echo "Uklanjanje:"
echo "   sudo apt remove $PKG"

if [ "${1:-}" = "--install" ]; then
    echo
    echo "→ instaliram…"
    sudo apt install -y "$OUT"
fi
