savedcmd_/home/Kernel/clique/click_sync_kernel.mod := printf '%s\n'   click_sync_kernel.o | awk '!x[$$0]++ { print("/home/Kernel/clique/"$$0) }' > /home/Kernel/clique/click_sync_kernel.mod
