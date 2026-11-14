"""Interface cloud privée du MVP Freelance Radar AI."""
from __future__ import annotations

import json
import hmac
from pathlib import Path
import streamlit as st

from radar import (
    DEFAULT_QUERIES, PROFILE_PATH, connect, export_csv, fetch_all, init_db,
    insert_signal, load_profile, outreach_draft, scan, update_signal,
    export_snapshot, import_snapshot
)

st.set_page_config(page_title="Freelance Radar AI", page_icon="📡", layout="wide")
st.markdown("""
<style>
.block-container {max-width:1280px;padding-top:1.75rem}
div[data-testid="stMetric"] {background:#f6f8fb;padding:18px;border-radius:12px;border:1px solid #e6eaf0}
.radar-note {padding:12px 16px;border-radius:10px;background:#edf4fc;color:#214c75}
</style>
""", unsafe_allow_html=True)

# Sécurité : application verrouillée tant que le mot de passe n'a pas été
# défini dans les secrets Streamlit, puis saisi dans la session du navigateur.
try:
    app_password = st.secrets.get("APP_PASSWORD", "")
except Exception:
    # En absence de secrets locaux, l’app reste volontairement verrouillée.
    app_password = ""

if not isinstance(app_password, str) or len(app_password) < 12:
    st.error("Configuration requise : définis APP_PASSWORD (12 caractères minimum) dans les secrets de ton application Streamlit Cloud.")
    st.info("Déploiement → Advanced settings → Secrets. Consulte DEPLOIEMENT_IPHONE.md. Aucun contenu métier n'est accessible tant que la configuration n'est pas terminée.")
    st.stop()

if not st.session_state.get("radar_authenticated", False):
    st.title("📡 Freelance Radar AI")
    st.caption("Accès sécurisé à ton radar de prospection")
    with st.form("login_form", clear_on_submit=True):
        password_input = st.text_input("Mot de passe", type="password", autocomplete="current-password")
        login_clicked = st.form_submit_button("Se connecter", use_container_width=True)
    if login_clicked:
        if hmac.compare_digest(password_input, app_password):
            st.session_state.radar_authenticated = True
            st.rerun()
        else:
            st.error("Mot de passe incorrect.")
    st.stop()

with st.sidebar:
    st.success("Session ouverte")
    if st.button("🔒 Se déconnecter"):
        st.session_state.radar_authenticated = False
        st.rerun()

init_db()
profile = load_profile()

st.title("📡 Freelance Radar AI")
st.caption("MVP 0.2 Cloud · Signaux publics · Matching CV · Brouillons de prospection")
st.info("**Mode observation :** aucune candidature ni aucun email n'est envoyé automatiquement. Les signaux sont des indices, pas des missions confirmées.")

tab_radar, tab_scan, tab_contacts, tab_profile, tab_backup = st.tabs(["🎯 Opportunités", "🔎 Scanner", "✉️ Prospection", "⚙️ Profil", "💾 Sauvegarde"])

with tab_radar:
    colA, colB = st.columns([2,1])
    with colA:
        threshold = st.slider("Score minimal de pertinence", 0, 100, 65, 5)
    with colB:
        status_filter = st.selectbox("État", ["Tous", "À qualifier", "À contacter", "Contacté", "Écarté"])
    rows = fetch_all(minimum=threshold)
    if status_filter != "Tous":
        rows = [r for r in rows if r["status"] == status_filter]

    totals = fetch_all()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Signaux collectés", len(totals))
    m2.metric("Pistes ≥ 75", sum(r["score"] >= 75 for r in totals))
    m3.metric("À contacter", sum(r["status"] == "À contacter" for r in totals))
    m4.metric("Contactés", sum(r["status"] == "Contacté" for r in totals))
    if not rows:
        st.warning("Aucun signal à afficher. Lance le scan RSS depuis l'onglet « Scanner des sources » ou importe une information publique.")
    for r in rows:
        name = r["company"] or "Entreprise à identifier"
        heading = f"{r['score']}/100 · {name} · {r['signal_type']}"
        with st.expander(heading, expanded=False):
            st.markdown(f"**{r['title']}**")
            st.caption(f"Source : {r['source']}" + (f" | {r['publisher']}" if r['publisher'] else "") + (f" | Publié le {r['published']}" if r['published'] else ""))
            st.link_button("Ouvrir la source", r["url"])
            st.write(r["summary"] or "Pas de résumé disponible ; consulter la source.")
            st.write("**Analyse explicable :**", r["rationale"])
            st.write("**Positionnement proposé :**", r["position"])
            c1, c2 = st.columns(2)
            with c1:
                company = st.text_input("Entreprise (à vérifier)", value=r["company"], key="co_"+r["id"])
                status = st.selectbox("Statut", ["À qualifier", "À contacter", "Contacté", "Écarté"],
                                      index=["À qualifier", "À contacter", "Contacté", "Écarté"].index(r["status"]), key="st_"+r["id"])
            with c2:
                note = st.text_area("Note / hypothèse / vérification", value=r["note"], height=84, key="no_"+r["id"])
            if st.button("Enregistrer", key="save_"+r["id"]):
                update_signal(r["id"], {"company": company, "status": status, "note": note})
                st.success("Enregistré.")
                st.rerun()
    if rows:
        st.download_button("⬇️ Exporter les opportunités en CSV", export_csv(rows), "opportunites.csv", "text/csv")

with tab_scan:
    st.subheader("Recherche de signaux publics")
    st.write("Recherche dans des **flux RSS publics de presse**. Les résultats sont liés à leur source et dédupliqués. Un contrôle humain de la source reste nécessaire avant de prospecter.")
    queries = st.text_area("Une requête par ligne", "\n".join(DEFAULT_QUERIES), height=180)
    if st.button("Lancer un scan maintenant", type="primary"):
        query_list = [q.strip() for q in queries.splitlines() if q.strip()]
        if len(query_list) > 20:
            st.error("Limite MVP : 20 requêtes par scan.")
        else:
            with st.spinner("Interrogation des flux RSS..."):
                result = scan(query_list)
            st.success(f"{result['found']} résultats consultés, {result['added']} nouveaux signaux enregistrés.")
            for problem in result["errors"]:
                st.warning(problem)
    st.divider()
    st.subheader("Ajouter un signal vérifié manuellement")
    with st.form("add_signal"):
        title = st.text_input("Titre de l'information")
        company = st.text_input("Entreprise (facultatif)")
        url = st.text_input("URL de la publication (requise)")
        summary = st.text_area("Résumé factuel")
        publisher = st.text_input("Média / source", value="Source publique")
        submitted = st.form_submit_button("Enregistrer la piste")
        if submitted:
            try:
                added = insert_signal({"title": title, "company": company, "url": url,
                                       "summary": summary, "publisher": publisher, "source": "Import manuel"})
                st.success("Signal ajouté." if added else "Signal déjà présent (URL identique).")
            except ValueError as exc:
                st.error(str(exc))

with tab_contacts:
    st.subheader("Préparer une approche personnalisée")
    st.write("Les contacts doivent être identifiés dans des sources professionnelles légitimes. Cette version n'infère ni n'achète d'adresse personnelle et **n'envoie pas d'emails**.")
    options = fetch_all()
    if not options:
        st.warning("Ajoute d'abord une opportunité dans le radar.")
    else:
        names = {r["id"]: f"{r['score']}/100 · {(r['company'] or 'Entreprise inconnue')} · {r['title'][:85]}" for r in options}
        selected = st.selectbox("Opportunité", list(names), format_func=lambda k: names[k])
        item = next(r for r in options if r["id"] == selected)
        with st.form("contact_form_"+selected):
            col1,col2 = st.columns(2)
            with col1:
                cn = st.text_input("Nom professionnel du contact", value=item["contact_name"])
                ce = st.text_input("Email professionnel vérifié", value=item["contact_email"])
            with col2:
                cr = st.text_input("Fonction du contact", value=item["contact_role"])
                cs = st.text_input("Source de la coordonnée", value=item["contact_source"])
            dnc = st.checkbox("Ne plus contacter (opposition ou demande de retrait)", value=bool(item["do_not_contact"]))
            if st.form_submit_button("Enregistrer les coordonnées"):
                update_signal(selected, {"contact_name": cn, "contact_role": cr, "contact_email": ce,
                                         "contact_source": cs, "do_not_contact": dnc})
                st.success("Fiche mise à jour.")
                st.rerun()
        subject, body = outreach_draft(item, profile)
        if item["do_not_contact"]:
            st.error("Contact marqué « ne plus contacter ». Ne pas envoyer.")
        elif not item["contact_email"]:
            st.warning("Pas encore de contact professionnel vérifié : ne pas envoyer ce brouillon.")
        elif not item["contact_source"]:
            st.warning("La provenance de l'adresse professionnelle doit être renseignée avant un éventuel envoi.")
        st.text_input("Objet proposé", value=subject)
        st.text_area("Brouillon proposé (à relire)", value=body, height=340)
        st.download_button("Télécharger le brouillon", f"Objet : {subject}\n\n{body}",
                           "brouillon_prospection.txt", "text/plain")

with tab_profile:
    st.subheader("Profil extrait du CV")
    st.write("**Titre :**", profile["profile_label"])
    st.write("**Expérience :**", str(profile["experience_years"]) + " ans")
    st.write("**TJM de référence :**", f"{profile['daily_rate_eur_reference']} €/jour (à confirmer)")
    st.write("**Positionnements :**")
    for title, detail in profile["positionings"].items():
        st.markdown(f"- **{title} :** {detail}")
    st.write("**Compétences :**", ", ".join(profile["skills"]))
    st.write("**Expériences :**")
    for h in profile["experience_highlights"]:
        st.markdown(f"- {h}")
    st.caption("Aucune coordonnée personnelle extraite du CV n'est stockée dans ce fichier de profil.")
    st.divider()
    st.subheader("Ce qui fonctionne déjà / étapes suivantes")
    st.markdown("""
- ✅ Ingestion RSS et ajout manuel de signaux sourcés
- ✅ Déduplication en SQLite, scoring explicable, filtre et CSV
- ✅ Saisie de contacts professionnels, registre d'opposition, brouillons personnalisés
- ⏭️ Enrichissement IA pour une meilleure extraction des entreprises et des décideurs
- ⏭️ Connecteurs d'API autorisées pour les offres d'emploi et marchés publics
- ⏭️ Envoi autonome B2B avec vérifications, plafonds, gestion des oppositions et suivi de réponse
- ⏭️ Hébergement / déclenchement programmé du scan
""")
    st.info("Hébergement cloud : le fichier SQLite local n'est **pas un stockage permanent**. Effectue des sauvegardes depuis l'onglet 💾 ou connecte une base cloud avant une utilisation sérieuse. Aucune veille ne tourne en arrière-plan dans Streamlit.")

with tab_backup:
    st.subheader("Sauvegarder tes opportunités")
    st.warning("Sur Streamlit Community Cloud, les fichiers locaux peuvent être perdus lors d'un redémarrage ou redéploiement. Télécharge régulièrement une sauvegarde. Les fiches contacts qu'elle contient sont confidentielles.")
    data = export_snapshot()
    st.download_button(
        "⬇️ Télécharger une sauvegarde JSON",
        data=data,
        file_name="freelance_radar_backup.json",
        mime="application/json",
        use_container_width=True,
    )
    st.divider()
    st.subheader("Restaurer une sauvegarde")
    backup = st.file_uploader("Sélectionner un fichier JSON de sauvegarde", type=["json"])
    if backup is not None:
        if st.button("Importer les opportunités (sans écraser les fiches existantes)"):
            try:
                result = import_snapshot(backup.getvalue())
            except (ValueError, UnicodeError, json.JSONDecodeError) as exc:
                st.error(f"Sauvegarde non valide : {exc}")
            else:
                st.success(f"{result['added']} signaux réimportés ({result['skipped']} déjà présents).")
                st.rerun()
