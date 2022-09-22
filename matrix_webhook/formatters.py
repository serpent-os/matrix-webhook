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
    if headers["X-GitHub-Event"] == "push":
        pusher, repository, ref, a, b, c = (
            data[k] for k in ["pusher", "repository", "ref", "after", "before", "compare"]
        )
        pusher = f"[@{pusher['name']}](https://github.com/{pusher['name']})"
        # Since we use monorepos and use an org-wide webhook, let's add repo info too.
        repo = f"[{repository['full_name']}]({repository['url']})"
        # The commit shasum hashes are noisy, so just make the ref link to the full compare
        data["body"] = f"{repo}: {pusher} pushed on [{ref}]({c}):\n\n"
        for commit in data["commits"]:
            # We only really need the shortlog of each relevant commit
            shortlog = commit['message'].strip().split("\n")[0]
            data["body"] += f"- [{shortlog}]({commit['url']})\n"
    else:
        data["body"] = "notification from github"
    data["digest"] = headers["X-Hub-Signature-256"].replace("sha256=", "")
    return data


def gitlab_gchat(data, headers):
    """Pretty-print a gitlab notification preformatted for Google Chat."""
    data["body"] = re.sub("<(.*?)\\|(.*?)>", "[\\2](\\1)", data["body"], re.MULTILINE)
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
