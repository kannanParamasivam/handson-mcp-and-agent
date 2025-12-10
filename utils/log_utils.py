def log_message(actor: str, log_msg: str):
  message = f"\033[1;32m{actor}\033[0m: {log_msg}"  # \033[1;32m makes text bold and green, \033[0m resets
  banner_boundary = "=" * 50
  print(banner_boundary)
  print(message)
  print(banner_boundary)