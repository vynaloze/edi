from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


TIMEOUT = 20


def main():
    url = 'http://127.0.0.1:5000/'
    options = webdriver.FirefoxOptions()
    options.add_argument("--headless")
    driver = None
    try:
        driver = webdriver.Firefox(options=options)
        driver.get(url)

        # show the form
        driver.find_element(By.XPATH, '/html/body/input').click()
        WebDriverWait(driver, TIMEOUT).until(EC.element_to_be_clickable((By.XPATH, '/html/body/div/form/div/button')))

        # find correct answers
        correct_answers_elements = driver.find_elements(By.XPATH, '/html/body/div/form/div/p')[2:5]
        name, email, password = [e.text.split(':')[1].strip() for e in correct_answers_elements]

        # fill correct answers
        driver.find_element(By.XPATH, '//*[@id="email"]').send_keys(email)
        driver.find_element(By.XPATH, '//*[@id="name"]').send_keys(name)
        driver.find_element(By.XPATH, '//*[@id="password"]').send_keys(password)
        driver.find_element(By.XPATH, '//*[@id="password-repeat"]').send_keys(password)
        driver.find_element(By.XPATH, '//*[@id="answer"]/option[@value="correct"]').click()

        # submit form and show result
        driver.find_element(By.XPATH, '/html/body/div/form/div/button').click()
        print('Response:')
        print(driver.page_source)

    finally:
        if driver:
            driver.quit()


if __name__ == '__main__':
    main()
