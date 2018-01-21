# csec510-selinux-hwgrading

## About

This repository contains files related to one of the case studies that was part of our project on SELinux for the CSEC 510 Operating System Security course.

The aim of these case studies is to demonstrate the benefits of using SELinux, in order to do things that would otherwise not be possible using traditional Unix DAC alone.

Feel free to use whatever is contained in this repository, but keep the following two things in mind:

1. The code included can be potentially destructive (i.e. it can modify or delete data on your system). It should only ever be run in dedicated VMs for created for testing purposes and not on production systems.
2. Coming up with security policies that cannot be circumvented is hard work! We make no guarantees that the sample policies included here cannot be circumvented. In any case, that is not the purpose of these case studies. We just aim to show these policies can be used to protect against very specific offending behavior, in a manner that would not be possible unless SELinux is not used.

We are not SELinux experts! We're just learning about the basics ourselves. Keep this in mind if you ever decide to use our code in any way.

## Scenario Description

This case study is about a very realistic scenario. In fact, one of the authors of this project came across a very similar situation in real life, when he was grading student homework submissions for a course where he was the TA.

Two students (01 and 02) have been given a simple programming assignment. They are responsible for implementing a simple Python server that:

- Listens on port 80 for incoming TCP connections.
- Once a connection has been accepted, starts a loop that:
	- Attempts to read 2048 bytes from the socket stream, and
	- Write the reverse string back to the socket...
	- ...unless that string was "bye\n", in which case the server should terminate.

The students should implement their assignments in a single file. Student 01's file should be named `01.py`.

The students are expected to encrypt their files using the grader's PGP public key that they were given. The encrypted file should be called `01.py.gpg`.

Obviously, the grader will have to decrypt and execute the code sent by the students in order to grade it. Even though there are only two students, the grader is a little bit of an automation freak and feels an irresistable urge to create a script that automates this process. Maybe next semester there will be 200 students taking the course, and these scripts will come in handy then, who knows.

The grader wants to run a command, like `run-submission 01`, that will first decrypt the student submission and then execute it. Once the server has started, the grader will use `nc localhost 80` to open a connection to it and see if it is working as expected (well, I suppose our automation-loving grader would also have automated this part of the process too... but nevermind that, please).

Unfortunately, not everyone is very nice. Student 02 is one example. Not only is his implementation practically the same as that of 01 in terms of providing the required functionality, he also added couple of lines of code that is designed to extract the private key that the grader uses to decrypt the files being sent to him, to be used in some nefarious way in the future.

## Problem Description

The problem is due to the fact that the student submissions are _untrusted code_, but they nevertheless need to be executed with root privileges in order to perform as expected. This is because part of the homework specification is that the server should bind to TCP port 80, which is a restricted port. However, this will give full permissions over the host that the grader is using to the student code... which in the case of student 02 will be abused.

## Solution Description

Our grader knows of such a risk, and is therefore using an isolated VM for grading these submissions... but he wants to use the same VM for _everything_ related to the grading process, including the decryption. But this means that the private key used for decrypting the files has to be installed on that VM. _Temporal separation_ could be a solution (i.e. the key is deleted before running the untrusted code), but then the grader would have to install/remove the key every time he wants to decrypt someting. Maybe students will sent multiple submissions at different times? What if he forgets and executes code while the key is installed? Without something like SELinux, temporal separation (or some other means of separation, like doing the decryption on another computer) would have to be _the_ solution, because there is no other way of protecting our private key from the root user on the machine, which the student code is running as.

Thankfully, this is not the case if we are using SELinux.

Our solution depends on the __principle of least privilege__, which is a core concept in SELinux, and any _nondiscretionary access control_ system. That is, the student code should be running with the least amount of privileges required to do its job, and nothing else.

## Demo Walkthrough

### Student Submissions

The student code is located in the `student` directory: `student/01.py` and `student/02.py`.

### Generating the GPG Key

In the scenario, the grader needs to have generated a PGP key and shared the public key with the students beforehand.

Running `bin/create-gpg-key` will use the configuration under `gpg/config` to create and install a new PGP key using `gpg2` on the system being used. The name of the created key will be 'Grader'.

### Simulating Student Submissions

Executing `bin/send-student-submissions` will encrypt each file under `student/` with the public key of 'Grader' and place it in `grader/inbox`. `student/01.py` is encrypted and put in `grader/inbox/01.py.gpg`.

### Decrypting Student Submissions

Executing `bin/decrypt-student-submissions` will decrypt each file under `grader/inbox/` and put the result in `grader/submissions/`. It will also set make the file user executable.

### Running Student Submissions (Unsecure)

Executing `bin/run-submission-unsecure 01` will run student 01's submission. You can then verify that it is working as expected by running `nc localhost 80`, and typing in something. You should get the reversed string.

If you run `bin/run-submission-unsecure 02`, it will work just like 01, with one very important difference. `student/02.py` contains the following code:

    import os
    os.system("gpg2 --export-secret-keys --output /tmp/secret-keys --armor")
    os.system("chmod 666 /tmp/secret-keys")

This will export all the secret keys on the system and put them in `/tmp/secret-keys`, in a world-readable fashion. Note that the students have reason to expect that the host would contain the private key on it, as they are encrypting their submissions with a public key.

Well, student 02 would probably not be able to exfiltrate the file, even if it was world-readable, without having access to the VM that the grader is using... but this is just a proof-of-concept. The student could just as easily transmit the secret key to some remote location over the network.

### Installing the `hwgrading` SELinux Policy Module

The `hwgrading` SELinux policy module has been implemented under the `policy-module/` directory. Running `bin/enable-policy-module` will compile and install the policy module (assuming that the system you are working with supports that sort of thing). This should be done before `bin/run-submission-secure` can be used.

### Running Student Submissions (Secure)

Executing `bin/run-submissions-secure 01` works like its unsecure cousin, but does `chcon -t hwgrading_exec_t grader/submissions/01.py` prior to executing that file. We assume that the grader has SELinux enabled and in enforcing mode, has the `hwgrading` policy module enabled, and is acting as an unconfined user (i.e. `unconfined_u`) in a way that the initial context will be `unconfined_u:unconfined_r:unconfined_t`. This is the default arrangement for the root user when using the _Targeted Policy_ on Fedora 27. This will make that process perform a __domain transition__ to `hwgrading_t` (defined in the `hwgrading` policy module) when executed, and so the process will run only with the permissions explicitly granted to that type. Note that in SELinux, all permissions have to be explicitly granted. The `hwgrading` module allows sufficient permissions for both files to be executed and demonstrate the functionality required by the assignment. However, `02.py` will not be able to generate `/tmp/secret-keys`, because SELinux will prevent it from doing so. You can check the audit logs after running `bin/run-submissions-secure 02` to see the audit message generated by SELinux.

### Cleaning Up

Running `bin/clean` will:

- Remove the 'Grader' PGP key
- Remove the `hwgrading` SELinux module
- Clean up the working directory using `git clean`