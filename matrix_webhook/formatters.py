"""Formatters for matrix webhook."""

import re


def grafana(data, headers):
    """Pretty-print a Grafana (version 8 and older) notification."""
    text = ""
    if "ruleName" not in data and "alerts" in data:
        return grafana_9x(data, headers)
    if "title" in data:
        text = "#### " + data["title"] + "\n"
    if "message" in data:
        text = text + data["message"] + "\n\n"
    if "evalMatches" in data:
        for match in data["evalMatches"]:
            text = text + "* " + match["metric"] + ": " + str(match["value"]) + "\n"
    data["body"] = text
    return data


def grafana_9x(data, headers):
    """Pretty-print a Grafana newer than v9.x notification."""
    text = ""
    if "title" in data:
        text = "#### " + data["title"] + "\n"
    if "message" in data:
        text = text + data["message"].replace("\n", "\n\n") + "\n\n"
    data["body"] = text
    return data


def github(data, headers):
    """Pretty-print a github notification."""
    # TODO: Write nice useful formatters. This is only an example.
    #if headers["X-GitHub-Event"] == "push":
    #    pusher, ref, a, b, c = (
    #        data[k] for k in ["pusher", "ref", "after", "before", "compare"]
    #    )
    #    pusher = f"[@{pusher['name']}](https://github.com/{pusher['name']})"
    #    data["body"] = f"{pusher} pushed on {ref}: [{b} → {a}]({c}):\n\n"
    #    for commit in data["commits"]:
    #        data["body"] += f"- [{commit['message']}]({commit['url']})\n"
    #else:
    #    data["body"] = "notification from github"
    #data["digest"] = headers["X-Hub-Signature-256"].replace("sha256=", "")
    #return data
    return github_aerynos(data, headers)


def github_aerynos(data, headers):
    """Custom AerynOS handler for GH notifications."""
    repository = data['repository']
    # It doesn't make sense to show private commits in public, so turn that off
    if repository['private'] and repository['visibility'] == "private":
        pass
        # GH webhook will get a 400 return code w/missing body
    elif headers['X-GitHub-Event'] == "push":
        pusher, ref, compare, created, deleted, forced = (
            data[k] for k in ["pusher", "ref", "compare", "created", "deleted", "forced"]
        )
        pusher_url = f"[@{pusher['name']}](https://github.com/{pusher['name']})"
        # Since we use monorepos and use an org-wide webhook, let's add repo info too.
        repo_url = f"[{repository['full_name']}]({repository['html_url']})"

        if len(data['commits']) == 0:
            # these are booleans
            created, deleted, forced = (data[k] for k in ["created", "deleted", "forced"])
            # `git push --tags` has empty commit field, but mentions refs/tags/<the-tag> in ref
            if "refs/tags/" in ref:
                tag = ref.split("/")[-1]
                tag_url = f"{repository['html_url']}/releases/tag/{tag}"
                data['body'] = f"{repo_url}: {pusher_url} pushed tag [{tag}]({tag_url})\n"
            elif created:
                data['body'] = f"{repo_url}: {pusher_url} created empty branch _{ref}_\n"
            elif deleted:
                data['body'] = f"{repo_url}: {pusher_url} deleted branch <del>{ref}</del>\n"
            elif forced:
                branch = ref.split("/")[-1]
                branch_url = f"{repository['html_url']}/commits/{branch}"
                data['body'] = f"{repo_url}: {pusher_url} force pushed on [{ref}]({branch_url})\n"
            # Yet to be understood scenario
            else:
                pass
        else:
            # The commit shasum hashes are noisy, so just make the ref link to the full compare
            data['body'] = f"{repo_url}: {pusher_url} "
            if forced:
                data['body'] += "force "
            data['body'] += f"pushed on [{ref}]({compare}):\n\n"

        for idx, commit in enumerate(data['commits']):
            # Elide commit list once we go past a reasonable number of commits for readability
            if idx >= 4:
                data['body'] += f"- (... {len(data['commits']) - 4} more commits ...)"
                break
            # We only really need the shortlog of each relevant commit
            shortlog = commit['message'].strip().split("\n")[0]
            data['body'] += f"- [{shortlog}]({commit['url']})\n"
    elif headers['X-GitHub-Event'] == "pull_request":
        action, number, pr, sender = (
            data[k] for k in ["action", "number", "pull_request", "sender"]
        )
        # avoid PR spam and wasted CPU cycles
        if action in ["opened", "closed", "reopened", "ready for review", "review requested"]:
            pr_title = pr['title']
            pr_url = pr['html_url']
            reponame = repository['full_name']
            repo_url = repository['html_url']
            # the user associated with the actual action, not just the PR
            sender_user = sender['login']
            url_query = "pulls/"

            if action == "closed":
                url_query="pulls/?q=is%3Apr+is%3Aclosed"

            data['body'] = f"PR#{number} [{pr_title}]({pr_url})\n\n"
            data['body'] += f"{action} by [@{sender_user}](https://github.com/{sender_user}) "
            data['body'] += f"in [{reponame}]({repo_url}/{url_query})"
        # endif
        # GH webhook will get a 400 return code w/missing body if the action
        # isn't in the allow-list
    else:
        event = headers['X-GitHub-Event']
        data['body'] = f"unsupported github event: '{event}'"
    data['digest'] = headers['X-Hub-Signature-256'].replace("sha256=", "")
    return data


def gitlab_gchat(data, headers):
    """Pretty-print a gitlab notification preformatted for Google Chat."""
    data["body"] = re.sub(
        "<(.*?)\\|(.*?)>",
        "[\\2](\\1)",
        data["body"],
        flags=re.MULTILINE,
    )
    return data


def gitlab_teams(data, headers):
    """Pretty-print a gitlab notification preformatted for Microsoft Teams."""
    body = []
    for section in data["sections"]:
        if "text" in section.keys():
            text = section["text"].split("\n\n")
            text = ["* " + t for t in text]
            body.append("\n" + "  \n".join(text))
        elif all(
            k in section.keys()
            for k in ("activityTitle", "activitySubtitle", "activityText")
        ):
            text = section["activityTitle"] + " " + section["activitySubtitle"] + " → "
            text += section["activityText"]
            body.append(text)

    data["body"] = "  \n".join(body)
    return data


def gitlab_webhook(data, headers):
    """Pretty-print a gitlab notification.

    NB: This is a work-in-progress minimal example for now
    """
    body = []

    event_name = data["event_name"]
    user_name = data["user_name"]
    project = data["project"]

    body.append(f"New {event_name} event")
    body.append(f"on [{project['name']}]({project['web_url']})")
    body.append(f"by {user_name}.")

    data["body"] = " ".join(body)
    if "X-Gitlab-Token" in headers:
        data["key"] = headers["X-Gitlab-Token"]
    return data


def grn(data, headers):
    """Pretty-print a github release notifier (grn) notification."""
    version, title, author, package = (
        data[k] for k in ["version", "title", "author", "package_name"]
    )
    data["body"] = (
        f"### {package} - {version}\n\n{title}\n\n"
        f"[{author} released new version **{version}** for **{package}**]"
        f"(https://github.com/{package}/releases/tag/{version}).\n\n"
    )

    return data
