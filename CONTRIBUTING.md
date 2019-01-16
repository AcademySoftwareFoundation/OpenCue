Contributing to OpenCue
===========================

Code contributions to OpenCue are welcome! Please review this document to get
a briefing on our process.


Mail List
---------

Contributors should be reading the opencue-dev mail list:

* [opencue-dev](https://groups.google.com/group/opencue-dev)

You can sign up for the mail list on your own using the link above.


Bug Reports and Issue Tracking
------------------------------

We use GitHub's issue tracking system for bugs and enhancements:
https://github.com/imageworks/OpenCue/issues

**If you are merely asking a question ("how do I...")**, please do not file an
issue, but instead ask the question on the [OpenCue developer mail
list](http://groups.google.com/group/opencue-dev).

If you are submitting a bug report, please be sure to note which version of
OpenCue you are using, which component of OpenCue you're having problems with,
and on what platform. Please give an account of

* what you tried
* what happened
* what you expected to happen instead

with enough detail that others can reproduce the problem.


Contributor License Agreement (CLA) and Intellectual Property
-------------------------------------------------------------

To protect the project -- and the contributors! -- we do require a
Contributor License Agreement (CLA) for anybody submitting changes.

* If you are an individual writing the code on your own time and you're SURE
you are the sole owner of any intellectual property you contribute, use the
[Individual CLA](http://opensource.imageworks.com/cla/pdf/Imageworks_Contributor_License_Agreement_Individual.pdf).

* If you are writing the code as part of your job, or if there is any
possibility that your employers might think they own any intellectual
property you create, then you should use the [Corporate
CLA](http://opensource.imageworks.com/cla/pdf/Imageworks_Contributor_License_Agreement_Corporate.pdf).

Download the appropriate CLA from the links above, print, sign, and rescan
it (or just add a digital signature directly), and email it to:
opensource@imageworks.com

Our CLA's are based on those used by Apache and many other open source
projects.


Pull Requests and Code Review
-----------------------------

The best way to submit changes is via GitHub Pull Request. GitHub has a
[Pull Request Howto](https://help.github.com/articles/using-pull-requests/).

All code must be formally reviewed before being merged into the official
repository. The protocol is like this:

1. Get a GitHub account, fork imageworks/OpenCue to create your
own repository on GitHub, and then clone it to get a repository on your
local machine.

2. Edit, compile, and test your changes. The Dockerfiles included with each
component can be helpful in creating an environment in which to do this.

3. Push your changes to your fork (each unrelated pull request to a separate
"topic branch", please).

4. Make a "pull request" on GitHub for your patch.

5. If your patch will induce a major compatibility break, or has a design
component that deserves extended discussion or debate among the wider OpenCue
community, then it may be prudent to email opencue-dev pointing everybody to
the pull request URL and discussing any issues you think are important.

6. The reviewer will look over the code and critique on the "comments" area,
or discuss in email. Reviewers may ask for changes, explain problems they
found, congratulate the author on a clever solution, etc. But until somebody
says "LGTM" (looks good to me), the code should not be committed. Sometimes
this takes a few rounds of give and take. Please don't take it hard if your
first try is not accepted. It happens to all of us.

7. After approval, one of the senior developers (with commit approval to the
official main repository) will merge your fixes into the master branch.

